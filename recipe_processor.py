#!/usr/bin/env python3
"""
Recipe Book Processor
Main Street Partners Coding Exercise

A Python module that processes recipe data from Excel files and generates summary reports.
"""

import argparse
import pandas as pd
from pathlib import Path
from lookups import temperature_lookup, duration_lookup
import logging


class LookupMatcher:
    """Helper class for bad/simple fuzzy matching lookup keys. Edit distance felt too complicated for this simple use case."""
    
    @staticmethod
    def find_match(key, lookup_dict):
        """Find a match for key in lookup_dict using substring matching."""
        # Direct lookup first
        if key in lookup_dict:
            return key
        
        # Substring matching: check if key is in any of the lookup keys
        key_lower = str(key).lower()
        for lookup_key in lookup_dict:
            if key_lower in lookup_key.lower() or lookup_key.lower() in key_lower:
                return lookup_key
        
        # No match found
        return None


class RecipeProcessor:
    """Main class"""
    
    def __init__(self, excel_file="recipe_book.xlsx", dry_run=False):
        self.excel_file = excel_file
        self.excel_file = Path(excel_file)
        self.dataframes = {}    # dict of dataframes for each sheet in the excel file
        self.temperature_lookup = temperature_lookup
        self.duration_lookup = duration_lookup
        self.dry_run = dry_run
        self.logger = logging.getLogger(__name__)
        
        # Configure logging
        if not self.logger.handlers:
            logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
        
        self.logger.info(f"Initializing RecipeProcessor with file {self.excel_file}")
    
    def load_excel_sheets(self):
        """Load all sheets from the Excel file into separate dataframes."""
        try:
            excel_file = pd.ExcelFile(self.excel_file)
            self.dataframes = {sheet_name: pd.read_excel(self.excel_file, sheet_name=sheet_name) 
                              for sheet_name in excel_file.sheet_names}
            # for exploration, print the first 5 rows of each sheet
            if self.dry_run:
                for sheet_name, sheet_df in self.dataframes.items():
                    self.logger.info(f"First 5 rows of {sheet_name}:")
                    self.logger.info(sheet_df.head(5))
                    self.logger.info("-" * 50)
                self.logger.info(f"Loaded {len(self.dataframes)} sheets: {list(self.dataframes.keys())}")
        except Exception as e:
            self.logger.error(f"Error loading Excel file: {e}")
            raise

    def get_sheet(self, sheet_name):
        """Get a dataframe from the Excel file."""
        return self.dataframes[sheet_name]
    
    def calculate_recipe_costs(self):
        """Calculate recipe costs using ingredient mapping and cost data."""
        dish_df = self.get_sheet('dish')
        dish_ingredient_df = self.get_sheet('dish_ingredient')
        ingredient_cost_df = self.get_sheet('ingredient_cost')
        
        # Create cost lookup dictionary
        cost_lookup = dict(zip(ingredient_cost_df['ingredient'], ingredient_cost_df['cost']))
        
        # Create ingredient mapping for each dish
        dish_ingredients = {}
        for _, row in dish_ingredient_df.iterrows():
            dish = row['dish']
            ingredient = row['ingredient']
            mapping = row['ingredient_map']
            if dish not in dish_ingredients:
                dish_ingredients[dish] = {}
            
            # Check if ingredient exists in cost lookup
            if ingredient in cost_lookup:
                dish_ingredients[dish][mapping] = cost_lookup[ingredient]
            else:
                self.logger.warning(f"Missing ingredient cost for '{ingredient}' in dish '{dish}' (mapped as '{mapping}')")
                dish_ingredients[dish][mapping] = float('nan')
        
        # Calculate costs for each dish
        recipe_costs = {}
        for _, row in dish_df.iterrows():
            dish = row['dish']
            formula = row['recipe_cost']
            ingredients = dish_ingredients.get(dish, {})
            
            # Replace variables in formula with actual costs
            try:
                # Replace A, B, etc. with actual values
                formula_eval = formula
                for var, cost in ingredients.items():
                    formula_eval = formula_eval.replace(var, str(cost))
                
                self.logger.debug(f"Dish '{dish}': formula '{formula}' -> '{formula_eval}'")
                
                # Check if formula contains NaN
                if 'nan' in formula_eval:
                    self.logger.warning(f"Formula for '{dish}' contains missing ingredients: {formula_eval}")
                    recipe_costs[dish] = float('nan')
                else:
                    # Evaluate the formula safely
                    recipe_costs[dish] = eval(formula_eval)
            except Exception as e:
                self.logger.error(f"Error evaluating formula for '{dish}': {e}")
                recipe_costs[dish] = float('nan')
        
        self.recipe_costs = recipe_costs
        self.logger.info(f"Calculated recipe costs: {recipe_costs}")

    # helper funcs to get temperature and duration from lookups.py, using substring matching for the temperature lookup
    def get_temperature(self, temp_key):
        """Get temperature from lookups.py with substring matching."""
        matched_key = LookupMatcher.find_match(temp_key, self.temperature_lookup)
        
        if matched_key:
            if matched_key != temp_key:
                self.logger.debug(f"Fuzzy matched temperature '{temp_key}' to '{matched_key}'")
            return self.temperature_lookup[matched_key]
        
        # If match isn't found, return NaN, let downstream code handle the error
        self.logger.warning(f"Temperature key '{temp_key}' not found. Available: {list(self.temperature_lookup.keys())}")
        return float('nan')

    def get_duration_lookup(self, duration_key):
        """Get duration from lookups.py."""
        try: 
            return self.duration_lookup[duration_key]
        except KeyError:
            self.logger.error(f"Duration key {duration_key} not found in duration lookup")
            return float('nan')
    
    def calculate_energy_flags(self):
        """Calculate energy values and identify the most energy dish."""
        dish_df = self.get_sheet('dish')
        
        # calc energy for each dish (temp_degC * time_mins)
        energies = {}
        for _, row in dish_df.iterrows():
            dish = row['dish']
            temp_key = row['temperature']
            duration_key = row['duration']
            
            temp_degC = self.get_temperature(temp_key)
            time_mins = self.get_duration_lookup(duration_key)
            
            energy = temp_degC * time_mins
            energies[dish] = energy
        
        # Find the maximum energy
        max_energy = max(energies.values())
        
        # Create most_energy flags
        self.most_energy_flags = {dish: (energy == max_energy) for dish, energy in energies.items()}
        self.energies = energies
        
        self.logger.info(f"Energies: {energies}")
        self.logger.info(f"Most energy flags: {self.most_energy_flags}")
    
    
    def generate_summary(self):
        """Generate the final summary dataframe."""
        dish_df = self.get_sheet('dish')
        
        summary_data = []
        for _, row in dish_df.iterrows():
            dish = row['dish']
            temp_key = row['temperature']
            duration_key = row['duration']
            
            # Get calculated values
            recipe_cash_cost = self.recipe_costs.get(dish, float('nan'))
            temp_degC = self.get_temperature(temp_key)
            time_mins = self.get_duration_lookup(duration_key)
            most_energy = self.most_energy_flags.get(dish, False)
            
            summary_data.append({
                'dish': dish,
                'recipe_cash_cost': recipe_cash_cost,
                'temp_degC': temp_degC,
                'time_mins': time_mins,
                'most_energy': most_energy
            })
        
        summary_df = pd.DataFrame(summary_data)
        self.logger.info(f"Generated summary with {len(summary_df)} rows")
        return summary_df
    
    
    def save_to_csv(self, output_file="summary.csv"):
        """Save the summary dataframe to CSV."""
        if self.dry_run:
            print(f"DRY RUN: Would save to {output_file}")
            return
        
        try:
            summary_df = self.generate_summary()
            
            # Round numeric columns for cleaner output and handle NaN display
            summary_df['recipe_cash_cost'] = summary_df['recipe_cash_cost'].round(2)
            
            # Save with na_rep='NaN' to show NaN instead of empty cells
            summary_df.to_csv(output_file, index=False, na_rep='NaN')
            self.logger.info(f"Saved summary to {output_file}")
            print(f"Summary saved to {output_file}")
        except Exception as e:
            self.logger.error(f"Error saving CSV: {e}")
            raise
    
    def process(self):
        """Main processing pipeline."""
        print("Starting recipe processing...")
        self.load_excel_sheets()
        self.calculate_recipe_costs()
        self.calculate_energy_flags()
        summary_df = self.generate_summary()
        self.save_to_csv()
        self.logger.info("Processing complete!")
        return summary_df


def main():
    """Main entry point with command line interface."""
    parser = argparse.ArgumentParser(description="Process recipe book data and generate summary, file is optional and defaults to recipe_book.xlsx")
    parser.add_argument('-e', '--execute', action='store_true', help='Run the program')
    parser.add_argument('--file', default='recipe_book.xlsx', help='Excel file to process')
    parser.add_argument('--dry-run', action='store_true', help='Dry run the program')
    
    args = parser.parse_args()
    
    if args.execute or args.dry_run:
        processor = RecipeProcessor(excel_file=args.file, dry_run=args.dry_run)
        processor.process()
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
# Coding Exercise

## Objective
Produce a solution that is a python module (not a python script) that takes a command line parameter `[h|e]`

* `-h, --help` will show help
* `-e, --execute` will run the program

The program will read into distinct pandas dataframes all of the sheets in the workbook `.\recipe_book.xlsx`

Output to a csv file called `.\summary.csv` a dataframe with the structure:

|dish|recipe_cash_cost|temp_degC|time_mins|most_energy|
|----|----------------|---------|---------|-----------|
| roast|11.4|200|75.5|False|
| boiled|7.1|180|60.0|False|
| sautée|NaN|160|99.0|True|
| creole|22.75|200|75.5|False|

* `recipe_cash_cost` evaluates the formula in sheet `dish` column `recipe_cost` using sheet `dish_ingredient` column `ingredient_map` for the ingredients and sheet `ingredient_cost` for the costs to insert into the formula
* `temp_degC` is set from `temperature_lookup` in `lookups.py` (using coding techniques not cut/paste for avoidance of doubt)
* `time_mins` is set from the `duration_lookup` in `lookups.py` (using coding techniques not cut/paste for avoidance of doubt)
* `most_energy` is a boolean flag set for the dish with the maximum energy, energy defined by `temp_degC * time_mins`

`.\recipe_book_5k.xlsx` is included for performance testing.

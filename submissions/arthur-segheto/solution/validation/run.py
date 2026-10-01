import pandas as pd

from scoring.data import loadPipeline, splitClosedAndOpenDeals
from validation.backtest import summarizeBacktest

closedDeals, _ = splitClosedAndOpenDeals(loadPipeline())
pd.options.display.float_format = "{:,.3f}".format
print(summarizeBacktest(closedDeals).to_string(index=False))

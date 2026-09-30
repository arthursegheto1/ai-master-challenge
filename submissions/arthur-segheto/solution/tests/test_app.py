from pathlib import Path

from streamlit.testing.v1 import AppTest

APP_PATH = Path(__file__).resolve().parent.parent / "app.py"
APP_TIMEOUT_SECONDS = 120


def startApp():
    return AppTest.from_file(str(APP_PATH), default_timeout=APP_TIMEOUT_SECONDS).run()


def testAppStartsWithoutErrors():
    assert not startApp().exception


def testAppShowsTheFourKpis():
    assert len(startApp().metric) >= 4


def testFilteringByRegionReducesTheOpenDeals():
    app = startApp()
    openDealsBefore = app.metric[0].value
    region = app.sidebar.multiselect[0].options[0]
    app.sidebar.multiselect[0].select(region).run()
    assert not app.exception
    assert app.metric[0].value != openDealsBefore

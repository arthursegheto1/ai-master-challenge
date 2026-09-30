import pytest

from scoring.data import loadPipeline, splitClosedAndOpenDeals
from scoring.priority import prioritize
from scoring.probability import buildWinModel


@pytest.fixture(scope="session")
def allDeals():
    return loadPipeline()


@pytest.fixture(scope="session")
def closedDeals(allDeals):
    return splitClosedAndOpenDeals(allDeals)[0]


@pytest.fixture(scope="session")
def openDeals(allDeals):
    return splitClosedAndOpenDeals(allDeals)[1]


@pytest.fixture(scope="session")
def winModel(closedDeals):
    return buildWinModel(closedDeals)


@pytest.fixture(scope="session")
def prioritizedDeals(openDeals, winModel):
    return prioritize(openDeals, winModel)

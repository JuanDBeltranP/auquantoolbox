from backtester.trading_system_parameters import TradingSystemParameters
from datetime import timedelta
from backtester.dataSource.quant_quest_data_source import QuantQuestDataSource
from backtester.executionSystem.simple_execution_system import SimpleExecutionSystem
from backtester.orderPlacer.backtesting_order_placer import BacktestingOrderPlacer
from backtester.trading_system import TradingSystem
from backtester.constants import *
from backtester.features.feature import Feature


class FeaturePredictionTradingParams(TradingSystemParameters):

    def __init__(self, problem2Solver):
        self.__problem2Solver = problem2Solver
        Problem2PredictionFeature.setProblemSolver(problem2Solver)
        self.__dataSetId = problem2Solver.getTrainingDataSet()
        super(FeaturePredictionTradingParams, self).__init__()

    def getStartingCapital(self):
        instrumentIds = self.__problem2Solver.getSymbolsToTrade()
        if instrumentIds and len(instrumentIds) > 0:
            return len(instrumentIds) * 1000000
        return 50000000
    '''
    Returns an instance of class DataParser. Source of data for instruments
    '''

    def getDataParser(self):
        instrumentIds = self.__problem2Solver.getSymbolsToTrade()
        return QuantQuestDataSource(cachedFolderName='historicalData/',
                                    dataSetId=self.__dataSetId,
                                    instrumentIds=instrumentIds)

    '''
    Returns a timedetla object to indicate frequency of updates to features
    Any updates within this frequncy to instruments do not trigger feature updates.
    Consequently any trading decisions that need to take place happen with the same
    frequency
    '''

    def getFrequencyOfFeatureUpdates(self):
        return timedelta(0, 30)  # minutes, seconds

    def getBenchmark(self):
        return None

    '''
    This is a way to use any custom features you might have made.
    Returns a dictionary where
    key: featureId to access this feature (Make sure this doesnt conflict with any of the pre defined feature Ids)
    value: Your custom Class which computes this feature. The class should be an instance of Feature
    Eg. if your custom class is MyCustomFeature, and you want to access this via featureId='my_custom_feature',
    you will import that class, and return this function as {'my_custom_feature': MyCustomFeature}
    '''

    def getCustomFeatures(self):
        return dict(self.__problem2Solver.getCustomFeatures(),
                    **{'problem2_prediction': Problem2PredictionFeature})

    '''
    Returns a dictionary with:
    key: string representing instrument type. Right now INSTRUMENT_TYPE_OPTION, INSTRUMENT_TYPE_STOCK, INSTRUMENT_TYPE_FUTURE
    value: Array of instrument feature config dictionaries
        feature config Dictionary has the following keys:
        featureId: a string representing the type of feature you want to use
        featureKey: {optional} a string representing the key you will use to access the value of this feature.
                    If not present, will just use featureId
        params: {optional} A dictionary with which contains other optional params if needed by the feature
    Example:
    positionConfigDict = {'featureId': 'position'}
    vwapConfigDict = {'featureKey': 'price',
                          'featureId': 'vwap'}
    movingAvg_30Dict = {'featureKey': 'mv_avg_30',
                          'featureId': 'moving_average',
                          'params': {'days': 30}}
    movingAvg_30Dict = {'featureKey': 'mv_avg_30',
                          'featureId': 'moving_average',
                          'params': {'days': 30}}
    return {INSTRUMENT_TYPE_FUTURE: [positionConfigDict, vwapConfigDict],
            INSTRUMENT_TYPE_STOCK: [positionConfigDict, movingAvg_30Dict, movingAvg_30Dict]}

    For each future instrument, you will have features keyed by position and price.
    For each stock instrument, you will have features keyed by position, mv_avg_30, mv_avg_30
    '''

    def getInstrumentFeatureConfigDicts(self):
        # ADD RELEVANT FEATURES HERE
        stockFeatureConfigs = self.__problem2Solver.getFeatureConfigDicts()
        classifierPrediction = {'featureKey': 'prediction',
                                'featureId': 'problem2_prediction',
                                'params': {}}
        scoreDict = {'featureKey': 'score',
                     'featureId': 'score_ll',
                     'params': {'predictionKey': 'prediction',
                                'target': 'Y'}}

        return {INSTRUMENT_TYPE_STOCK: stockFeatureConfigs + [classifierPrediction, scoreDict]}
    '''
    Returns an array of market feature config dictionaries
        market feature config Dictionary has the following keys:
        featureId: a string representing the type of feature you want to use
        featureKey: a string representing the key you will use to access the value of this feature.this
        params: A dictionary with which contains other optional params if needed by the feature
    '''

    def getMarketFeatureConfigDicts(self):
        # ADD RELEVANT FEATURES HERE

        # customFeatureDict = {'featureKey': 'custom_mrkt_feature',
        #                      'featureId': 'my_custom_mrkt_feature',
        #                      'params': {'param1': 'value1'}}
        scoreDict = {'featureKey': 'score',
                     'featureId': 'score_ll',
                     'params': {'featureName': self.getPriceFeatureKey(),
                                'instrument_score_feature': 'score'}}
        return [scoreDict]

    '''
    Returns the type of execution system we want to use. Its an implementation of the class ExecutionSystem
    It converts prediction to intended positions for different instruments.
    '''

    def getExecutionSystem(self):
        return SimpleExecutionSystem(enter_threshold=0.8, exit_threshold=0.6,
                                     longLimit=10000, shortLimit=10000, capitalUsageLimit=0.05,
                                     lotSize=500, limitType='L', price=self.getPriceFeatureKey())

    '''
    Returns the type of order placer we want to use. its an implementation of the class OrderPlacer.
    It helps place an order, and also read confirmations of orders being placed.
    For Backtesting, you can just use the BacktestingOrderPlacer, which places the order which you want, and automatically confirms it too.
    '''

    def getOrderPlacer(self):
        return BacktestingOrderPlacer()

    '''
    Returns the amount of lookback data you want for your calculations. The historical market features and instrument features are only
    stored upto this amount.
    This number is the number of times we have updated our features.
    '''

    def getLookbackSize(self):
        return 90

    def getPriceFeatureKey(self):
        return 'stockVWAP'

    def getDataSetId(self):
        return self.__dataSetId

    def setDataSetId(self, dataSetId):
        self.__dataSetId = dataSetId


class Problem2PredictionFeature(Feature):
    problem2Solver = None

    @classmethod
    def setProblemSolver(cls, problem2Solver):
        Problem2PredictionFeature.problem2Solver = problem2Solver

    @classmethod
    def computeForInstrument(cls, updateNum, time, featureParams, featureKey, instrumentManager):
        return Problem2PredictionFeature.problem2Solver.getClassifierProbability(updateNum, time, instrumentManager)


if __name__ == "__main__":
    tsParams = MyTradingParams()
    tradingSystem = TradingSystem(tsParams)
    tradingSystem.startTrading(onlyAnalyze=True, shouldPlot=True)

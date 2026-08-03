from strategies.base import BaseStrategy
from strategies.scalping_rsi_vwma import ScalpingStrategyRSI_VWMA
from strategies.trend_following import TrendFollowingStrategy
from strategies.scalping import ScalpingStrategy
from strategies.trend_following_adx import TrendFollowingADX
from strategies.scalping_dmi_macd import ScalpingStrategyDMI_MACD
from strategies.scalping_bb_macd_tm import ScalpingStrategyBB_MACD_TM
from strategies.scalping_hma_stoch import ScalpingStrategyHMA_Stoch
from strategies.scalping_vwap_stochrsi import ScalpingStrategyVWAP_StochRSI
from strategies.trend_vwma_sott import TrendStrategyVWMA_SOTT
from strategies.trend_pmax_nsm import TrendStrategyPMax_NSM
from strategies.trend_aroon_rsi_sma import TrendStrategyAroonRSI_SMA


__all__ = ['BaseStrategy', 'ScalpingStrategyRSI_VWMA', 'TrendFollowingStrategy',
           'ScalpingStrategy', 'TrendFollowingADX','ScalpingStrategyDMI_MACD','ScalpingStrategyBB_MACD_TM'
          ,'ScalpingStrategyHMA_Stoch','ScalpingStrategyVWAP_StochRSI','TrendStrategyVWMA_SOTT','TrendStrategyPMax_NSM',
            'TrendStrategyAroonRSI_SMA',


]
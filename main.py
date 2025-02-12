from binance.client import Client
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import time
import os
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Initialize Binance client
client = Client(os.environ.get('0XlW2DdF8RKEq7YLQmxyQDTwUwfTOp4aGBi7KPrhNQCwZ0PNaevRSl8M985FMnP2'), os.environ.get('eSfUiy0oO10DZ6ziMddgJP6w2rpXVs89euAzzsXmlWdMJOn3NUeUUsLYYEuwwZdN'))

class BinanceLiquidationAnalyzer:
    def __init__(self):
        self.symbol = 'BTCUSDT'
        self.interval = Client.KLINE_INTERVAL_1HOUR
        self.lookback = 24  # Number of 1-hour candles to analyze
        self.long_signal_threshold = 0.01  # 1% above long liquidation level
        self.short_signal_threshold = 0.01  # 1% below short liquidation level
        self.max_leverage = 125  # Maximum leverage on Binance futures
        self.long_liq = None
        self.short_liq = None
        self.position = None

    def get_historical_klines(self):
        end_time = datetime.now()
        start_time = end_time - timedelta(hours=self.lookback)
        
        klines = client.get_historical_klines(
            self.symbol, 
            self.interval, 
            start_time.strftime("%d %b %Y %H:%M:%S"),
            end_time.strftime("%d %b %Y %H:%M:%S")
        )
        
        df = pd.DataFrame(klines, columns=['Open time', 'Open', 'High', 'Low', 'Close', 'Volume', 'Close time', 
                                           'Quote asset volume', 'Number of trades', 'Taker buy base asset volume', 
                                           'Taker buy quote asset volume', 'Ignore'])
        
        df['Open time'] = pd.to_datetime(df['Open time'], unit='ms')
        for col in ['Open', 'High', 'Low', 'Close', 'Volume']:
            df[col] = pd.to_numeric(df[col])
        
        return df

    def get_funding_rate(self):
        funding_rate = client.futures_funding_rate(symbol=self.symbol)[0]
        return float(funding_rate['fundingRate'])

    def get_open_interest(self):
        open_interest = client.futures_open_interest(symbol=self.symbol)
        return float(open_interest['openInterest'])

    def estimate_liquidation_levels(self, df):
        if self.long_liq is None or self.short_liq is None:
            current_price = df['Close'].iloc[-1]
            high_price = df['High'].max()
            low_price = df['Low'].min()
            
            # Estimate liquidation levels based on recent price action and max leverage
            self.long_liq = current_price * (1 - 1/self.max_leverage)
            self.short_liq = current_price * (1 + 1/self.max_leverage)
            
            # Adjust estimates based on recent price action
            self.long_liq = max(self.long_liq, low_price * 0.99)
            self.short_liq = min(self.short_liq, high_price * 1.01)
        
        return self.long_liq, self.short_liq

    def analyze_liquidation_risk(self, current_price):
        risk_levels = []
        
        long_distance = (current_price - self.long_liq) / current_price
        short_distance = (self.short_liq - current_price) / current_price
        
        if long_distance < 0.05:
            risk_levels.append(f"High risk of long liquidations around ${self.long_liq:,.2f}")
        elif long_distance < 0.1:
            risk_levels.append(f"Moderate risk of long liquidations around ${self.long_liq:,.2f}")
        
        if short_distance < 0.05:
            risk_levels.append(f"High risk of short liquidations around ${self.short_liq:,.2f}")
        elif short_distance < 0.1:
            risk_levels.append(f"Moderate risk of short liquidations around ${self.short_liq:,.2f}")
        
        return risk_levels

    def generate_trading_signals(self, current_price):
        signals = []
        
        if self.position is None:
            if current_price > self.long_liq * (1 + self.long_signal_threshold):
                signals.append("LONG SIGNAL: Open a long position.")
                self.position = "LONG"
            elif current_price < self.short_liq * (1 - self.short_signal_threshold):
                signals.append("SHORT SIGNAL: Open a short position.")
                self.position = "SHORT"
        elif self.position == "LONG" and current_price <= self.long_liq:
            signals.append("CLOSE LONG: Close the long position.")
            self.position = None
            self.long_liq = None
            self.short_liq = None
        elif self.position == "SHORT" and current_price >= self.short_liq:
            signals.append("CLOSE SHORT: Close the short position.")
            self.position = None
            self.long_liq = None
            self.short_liq = None
        
        return signals

    def run_analysis(self):
        try:
            klines_df = self.get_historical_klines()
            funding_rate = self.get_funding_rate()
            open_interest = self.get_open_interest()
            
            current_price = klines_df['Close'].iloc[-1]
            self.estimate_liquidation_levels(klines_df)
            
            risk_levels = self.analyze_liquidation_risk(current_price)
            signals = self.generate_trading_signals(current_price)
            
            os.system('cls' if os.name == 'nt' else 'clear')
            self.print_analysis(current_price, funding_rate, open_interest, risk_levels, signals)
            
        except Exception as e:
            logger.error(f"Error in run_analysis: {str(e)}")
            print(f"An error occurred: {str(e)}")

    def print_analysis(self, current_price, funding_rate, open_interest, risk_levels, signals):
        print("\n=== BTCUSDT Liquidation Analysis and Trading Signals ===")
        print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"\nCurrent Price: ${current_price:,.2f}")
        print(f"Funding Rate: {funding_rate:.4%}")
        print(f"Open Interest: {open_interest:,.0f} BTC")
        
        if self.long_liq and self.short_liq:
            print(f"\nEstimated Liquidation Levels:")
            print(f"Long Positions: ${self.long_liq:,.2f}")
            print(f"Short Positions: ${self.short_liq:,.2f}")
        
        print("\nLiquidation Risk Analysis:")
        for risk in risk_levels:
            print(f"- {risk}")

        print("\nTrading Signals:")
        if signals:
            for signal in signals:
                print(f"! {signal}")
        else:
            print("- No clear trading signals at the moment.")

        if self.position:
            print(f"\nCurrent Position: {self.position}")

def main():
    analyzer = BinanceLiquidationAnalyzer()
    while True:
        try:
            analyzer.run_analysis()
            print("\nNext update in 5 minutes...")
            time.sleep(30)  # Wait for 5 minutes before the next update
        except Exception as e:
            logger.error(f"Error in main loop: {str(e)}")
            print(f"An error occurred in the main loop: {str(e)}")
            print("Retrying in 60 seconds...")
            time.sleep(60)

if __name__ == "__main__":
    main()


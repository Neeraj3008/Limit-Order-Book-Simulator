import numpy as np

class market_analytics:
    def __init__(self,bucket_size = 50):
        self.bucket_size = bucket_size
        self.current_buy_vol = 0
        self.current_sell_vol = 0
        self.vpin_history = []

    def update(self, side: str , quantity = float):
        if side =="buy":
            self.current_buy_vol += quantity

        else:
            self.current_sell_vol += quantity 


        if (self.current_buy_vol + self.current_sell_vol) >= self.bucket_size:
            vpin = self._calculate_vpin()
            self.vpin_history.append(vpin)
            
            # Reset for next bucket
            self.current_buy_vol = 0
            self.current_sell_vol = 0
            return vpin
        return None


    def _calculate_vpin(self):
        # VPIN Formula: |Buy Vol - Sell Vol| / Total Vol
        imbalance = abs(self.current_buy_vol - self.current_sell_vol)
        total_vol = self.current_buy_vol + self.current_sell_vol
        return imbalance / total_vol if total_vol > 0 else 0

analytics = market_analytics(bucket_size=100)               
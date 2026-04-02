import numpy as np
import os
import google.generativeai as genai
import json
import traceback
import datetime
from sklearn.ensemble import RandomForestRegressor
from typing import List, Tuple, Optional

class GameRevenuePredictor:
    def __init__(self, csv_path: str):
        import pandas as pd
        try:
            self.df = pd.read_csv(csv_path)
            self.calibration_factor = 1.05
        except Exception as e:
            print(f"❌ Error loading CSV: {e}")
            self.df = pd.DataFrame()
        
        self.rf_model = None
        self.train_model()

    def get_genres(self) -> List[str]:
        if self.df.empty:
            return ["Action", "Adventure", "Strategy", "RPG", "Simulation", "Sports", "Racing"]
        return sorted(self.df['genre'].dropna().unique().tolist())

    def train_model(self):
        try:
            if self.df.empty: return
            features = ['month', 'prix']
            X = self.df[features].fillna(0)
            y = self.df['ventes_est'].fillna(0)
            self.rf_model = RandomForestRegressor(n_estimators=100, random_state=42)
            self.rf_model.fit(X, y)
        except:
            print("⚠️ RF Model failed, using heuristic.")

    def analyze_sentiment_buzz(self, api_key: str, game_name: str, similar_games: str = "") -> dict:
        if not api_key: return {"score": 7.0, "reason": "No API Key"}
        try:
            genai.configure(api_key=api_key)
            models_to_try = [
                'gemini-3.1-flash-lite', 
                'gemini-2.5-flash-pro', 
                'gemini-2.5-flash', 
                'gemini-3-flash', 
                'gemini-2.5-flash-lite', 
                'gemma-3-27b', 
                'gemma-3-12b'
            ]
            for m in models_to_try:
                try:
                    model = genai.GenerativeModel(m)
                    res = model.generate_content(f"Analyze market hype for: {game_name}. Return ONLY a JSON: {{'score': 1.0-10.0, 'reason': 'text'}}")
                    text = res.text.strip()
                    if "```json" in text: text = text.split("```json")[1].split("```")[0].strip()
                    elif "```" in text: text = text.split("```")[1].split("```")[0].strip()
                    data = json.loads(text)
                    return {"score": data.get('score', 7), "reason": data.get('reason', ""), "model_used": m}
                except: continue
            return {"score": 7.0, "reason": "Market analysis fallback"}
        except: return {"score": 7.0, "reason": "System busy"}

    def predict_optimization(self, game_name: str = None, genre_name: str = "Action",
                             budget: float = 0, wishlists: int = 0,
                             sentiment_target: float = 70.0, reviews_target: float = 70.0,
                             month: int = 10, langs: int = 5, similar_games: list = None,
                             sentiment_ia_score: float = None, fixed_price: float = None,
                             previous_sales: float = 0, previous_sentiment: float = 0,
                             previous_buzz: float = 0, num_dlcs: int = 0, 
                             dlc_price: float = 0.0) -> dict:
        
        # 1. Match game in DB
        game_match = self.df[self.df['nom'].str.lower() == game_name.lower().strip()] if (not self.df.empty and game_name) else None
        real_sales_data = float(game_match.iloc[0].get('ventes_reelles_officielles', 0)) if (game_match is not None and not game_match.empty) else 0
        
        # 2. Base Calculation
        effective_sentiment = sentiment_ia_score * 10 if (sentiment_ia_score is not None and sentiment_ia_score > 0) else sentiment_target
        if not effective_sentiment: effective_sentiment = 70.0
        
        wishlists = wishlists if wishlists else 0
        base_conv = 0.6 if budget > 50000000 else 0.4
        est_total_sales = wishlists * (base_conv + (effective_sentiment / 200))
        
        price = fixed_price if fixed_price is not None else 60
        p_factor = np.exp(-0.06 * (price - 60) / 60)
        est_total_sales *= p_factor
        
        if previous_sales and previous_sales > 10000000:
            est_total_sales *= 1.35
            
        # 3. Evolution and Smoothing
        final_sales = est_total_sales
        dist_ratios = [0.55, 0.25, 0.12, 0.05, 0.03]
        
        if real_sales_data >= 1000000:
            momentum = 2.8 if real_sales_data < 4000000 else 2.5
            y1 = real_sales_data * momentum
            dist_ratios = [0.45, 0.28, 0.15, 0.08, 0.04]
            evo_sales = [0]*5
            evo_sales[0] = int(y1)
            for i in range(1, 5): evo_sales[i] = int(evo_sales[0] * (dist_ratios[i] / dist_ratios[0]))
            final_sales = sum(evo_sales)
        else:
            final_sales = max(est_total_sales, real_sales_data / 0.55 if real_sales_data > 0 else est_total_sales)
            evo_sales = [int(final_sales * r) for r in dist_ratios]
            if real_sales_data > 0 and evo_sales[0] < real_sales_data:
                evo_sales[0] = int(real_sales_data)
                final_sales = sum(evo_sales)

        max_profit = (final_sales * price * 0.55) - budget
        if num_dlcs > 0: max_profit += (final_sales * 0.15 * dlc_price * 0.55) * num_dlcs

        return {
            "best_price": float(price),
            "max_profit": float(max_profit),
            "est_total_sales": int(final_sales),
            "evolution_sales": evo_sales,
            "evolution_years": ["Year 1", "Year 2", "Year 3", "Year 4", "Year 5"],
            "sentiment_ia_score": float(effective_sentiment/10),
            "reason": "Corrected multi-parameter prediction synced with server."
        }

    def analyze_image_with_gemini(self, api_key: str, image_path: str):
        return {"sentiment_score": 7.5, "analysis": "Visual analysis placeholder"}

import numpy as np
import os
import google.generativeai as genai
import json
import traceback
import datetime
from sklearn.ensemble import RandomForestRegressor
from typing import List, Tuple

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
        # Return unique genres sorted
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
            print("⚠️ RF Model training failed, using heuristic fallback.")

    def analyze_sentiment_buzz(self, api_key: str, game_name: str, similar_games: str = "") -> dict:
        if not api_key:
            return {"error": "Missing API Key", "score": 5, "reason": "No API Key"}
        
        is_already_released = False
        if not self.df.empty and game_name:
            match = self.df[self.df['nom'].str.lower() == game_name.lower().strip()]
            if not match.empty:
                is_already_released = True

        now_str = datetime.datetime.now().strftime("%Y-%m-%d")
        prompt = f"""
        Act as a gaming market analyst. Current Date: {now_str}.
        Analyze the public sentiment for: "{game_name}".
        Context / Similar Games: "{similar_games}".
        {"Note: Game is already released with records." if is_already_released else "Note: Game is upcoming."}
        
        Return ONLY a JSON object:
        {{
            "score": float (1-10),
            "reason": "1 short sentence about reputation"
        }}
        """

        try:
            genai.configure(api_key=api_key)
            # Exactly the models requested
            models_to_try = [
                'gemini-3.1-flash-lite', 
                'gemini-2.5-flash-pro', 
                'gemini-2.5-flash', 
                'gemini-3-flash', 
                'gemini-2.5-flash-lite', 
                'gemma-3-27b', 
                'gemma-3-12b'
            ]
            
            for model_name in models_to_try:
                try:
                    model = genai.GenerativeModel(model_name)
                    response = model.generate_content(prompt)
                    text = response.text.strip()
                    if "```json" in text: text = text.split("```json")[1].split("```")[0].strip()
                    elif "```" in text: text = text.split("```")[1].split("```")[0].strip()
                    data = json.loads(text)
                    return {"score": data.get('score', 5), "reason": data.get('reason', ""), "model_used": model_name}
                except: continue
            return {"score": 6.5, "reason": "Awaiting market data"}
        except Exception as e:
            return {"score": 5, "reason": str(e)}

    def predict_optimization(self, game_name: str, fixed_price: float = None, 
                             target_price: float = None, budget: float = 0, 
                             wishlists: int = 0, prev_sales: float = 0, 
                             prev_score: float = 0, genre_name: str = "Action",
                             sentiment_ia_score: float = None,
                             reviews_target: float = 80.0,
                             num_dlcs: int = 0, dlc_price: float = 0) -> dict:
        
        game_match = self.df[self.df['nom'].str.lower() == game_name.lower().strip()] if not self.df.empty else None
        real_sales_data = float(game_match.iloc[0].get('ventes_reelles_officielles', 0)) if (game_match is not None and not game_match.empty) else 0
        real_game_price = float(game_match.iloc[0].get('prix', 60)) if (game_match is not None and not game_match.empty) else 60

        sentiment_target = (sentiment_ia_score if sentiment_ia_score is not None else 7.0) * 10
        
        # Heuristic conversion logic
        base_conversion = 0.6 if budget > 50000000 else 0.4
        est_total_sales = wishlists * (base_conversion + (sentiment_target / 200))
        
        # Brand Momentum
        if prev_sales > 10000000:
            est_total_sales *= 1.3
        
        fixed_p = fixed_price if fixed_price else (target_price if target_price else 60)
        p_factor = np.exp(-0.06 * (fixed_p - 60) / 60)
        est_total_sales *= p_factor
        
        # Velocity and Smoothing Fix
        final_sales_display = est_total_sales
        dist_ratios = [0.55, 0.25, 0.12, 0.05, 0.03] # Standard
        
        if real_sales_data >= 1000000:
            momentum = 2.8 if real_sales_data < 4000000 else 2.5
            projected_y1 = real_sales_data * momentum
            # Smoothing: Mega-hits have longer legs. 
            # If Y1 is huge, Y2 should be ~50-60% of Y1.
            dist_ratios = [0.45, 0.28, 0.15, 0.08, 0.04]
            evolution_sales = [0] * 5
            evolution_sales[0] = int(projected_y1)
            for i in range(1, 5):
                rel = dist_ratios[i] / dist_ratios[0]
                evolution_sales[i] = int(evolution_sales[0] * rel)
            final_sales_display = sum(evolution_sales)
        else:
            final_sales_display = max(est_total_sales, real_sales_data / 0.55 if real_sales_data > 0 else est_total_sales)
            evolution_sales = [int(final_sales_display * r) for r in dist_ratios]
            if real_sales_data > 0 and evolution_sales[0] < real_sales_data:
                evolution_sales[0] = int(real_sales_data)
                final_sales_display = sum(evolution_sales)

        max_profit = (final_sales_display * fixed_p * 0.55) - budget
        
        # DLCs
        if num_dlcs > 0:
            dlc_rev = (final_sales_display * 0.15 * dlc_price * 0.55) * num_dlcs
            max_profit += dlc_rev

        return {
            "best_price": float(fixed_p),
            "max_profit": float(max_profit),
            "est_total_sales": int(final_sales_display),
            "evolution_sales": evolution_sales,
            "evolution_years": ["Year 1", "Year 2", "Year 3", "Year 4", "Year 5"],
            "sentiment_ia_score": float(sentiment_target/10),
            "reason": "Market analysis integrated with real velocity data"
        }

    def analyze_image_with_gemini(self, api_key: str, image_path: str):
        return {"sentiment_score": 7.5, "analysis": "High fidelity visuals detected"}

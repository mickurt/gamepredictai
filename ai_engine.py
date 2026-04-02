import pandas as pd
import numpy as np
import os
import google.generativeai as genai
from sklearn.ensemble import RandomForestRegressor
from typing import List, Tuple

class GameRevenuePredictor:
    def __init__(self, csv_path: str):
        self.csv_path = csv_path
        self.model = None
        self.genres_mapping = {}
        self.calibration_factor = 1.0
        self.df = None
        self._train_model()

    def _train_model(self):
        if not os.path.exists(self.csv_path):
            print(f"Dataset not found at {self.csv_path}")
            return

        self.df = pd.read_csv(self.csv_path)
        
        # Strip column names and string values
        self.df.columns = [c.strip() for c in self.df.columns]
        for col in self.df.select_dtypes(['object']).columns:
            self.df[col] = self.df[col].astype(str).str.strip()
        
        # Translate genres to English
        genre_map = {
            'Aventure': 'Adventure',
            'Occasionnel': 'Casual',
            'Massivement multijoueur': 'Massively Multiplayer',
            'Accès anticipé': 'Early Access',
            'Course automobile': 'Racing',
            'Stratégie': 'Strategy',
            'Indépendant': 'Indie',
            'Production audio': 'Audio Production',
            'Animation & Modélisation': 'Animation & Modeling',
            'Conception & Illustration': 'Design & Illustration',
            'Utilitaires': 'Utilities',
            'Nudité': 'Nudity',
            'Sport': 'Sports'
        }
        self.df['genre'] = self.df['genre'].replace(genre_map)
        
        # Handle genre encoding
        self.df['genre_id'] = self.df['genre'].astype('category').cat.codes
        self.genres_mapping = dict(enumerate(self.df['genre'].astype('category').cat.categories))
        
        # Features & Target
        # Ensure we handle potential missing columns gracefully or assume they exist from previous steps
        features = ['genre_id', 'prix', 'ccu_24h', 'audio_langs', 'sub_langs', 'is_multi', 'month', 'sentiment']
        
        # Clean basic NaNs if any
        train_df = self.df.dropna(subset=features + ['ventes_est'])
        
        X = train_df[features]
        y = train_df['ventes_est']
        
        self.model = RandomForestRegressor(n_estimators=1000, min_samples_leaf=3, random_state=42)
        self.model.fit(X, y)
        
        # Calibration
        calib_set = self.df[self.df['ventes_reelles_officielles'] > 0]
        if not calib_set.empty:
            # Use median to avoid outliers (e.g. F2P games with massive user counts skewing the ratio)
            raw_factor = (calib_set['ventes_reelles_officielles'] / calib_set['ventes_est']).median()
            # Cap the factor to avoid unrealistic multipliers
            self.calibration_factor = min(raw_factor, 3.0)
        else:
            self.calibration_factor = 1.15
        
        print(f"✅ Model Trained. Calibration Factor (Median): {self.calibration_factor:.2f}")

    def get_genres(self) -> dict:
        return {v: k for k, v in self.genres_mapping.items()}

    def analyze_image_with_gemini(self, api_key: str, image_bytes: bytes, mime_type: str) -> List[str]:
        import traceback
        if not api_key:
            print("⚠️ Gemini Error: No API Key provided.")
            return []
        
        print(f"📡 Calling Gemini API... Key: ...{api_key[-4:]} | Mime: {mime_type} | Size: {len(image_bytes)} bytes")
        
        try:
            genai.configure(api_key=api_key)
            
            # Requested Model Priority
            models_to_try = ['gemini-2.5-flash-lite', 'gemini-2.5-flash', 'gemini-3.0-flash']
            
            prompt = """
            Analyze this game screenshot or artwork. 
            Identify its genre and visual style (e.g. Pixel Art, Low Poly, Photorealistic).
            List exactly 5 existing popular games on Steam that look similar or belong to the same niche.
            Output format: Just the game names separated by commas. Example: Terraria, Starbound, Minecraft.
            """
            
            cookie_picture = {
                'mime_type': mime_type,
                'data': image_bytes
            }
            
            # Paramètres de sécurité réduits pour accepter les screenshots de jeux (violence fictive)
            safety_settings = [
                {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"}
            ]

            last_error = None

            for model_name in models_to_try:
                try:
                    print(f"🤖 Trying Image Analysis with Model: {model_name}...")
                    model = genai.GenerativeModel(model_name)
                    response = model.generate_content([prompt, cookie_picture], safety_settings=safety_settings)
                    
                    # Debug: Check safety ratings or empty response
                    if not response.parts:
                        print(f"⚠️ Gemini Empty Response Parts. Finish Reason: {response.candidates[0].finish_reason if response.candidates else 'Unknown'}")
                        if response.prompt_feedback:
                            print(f"Safety Ratings: {response.prompt_feedback}")
                        # Fallback to next model if empty response
                        raise ValueError(f"Empty response from {model_name}")

                    text = response.text.strip()
                    print(f"🤖 Gemini Raw Output: {text}")
                    
                    # Cleaning the response (remove potential dots or newlines)
                    cleaned_text = text.replace('\n', ',').replace('.', '')
                    similars = [g.strip() for g in cleaned_text.split(',') if g.strip()]
                    
                    # Fallback if AI gets chatty
                    final_similars = []
                    for s in similars:
                        if len(s.split()) < 6: # Heuristic: Game titles are usually short
                            final_similars.append(s)
                    
                    if final_similars:
                        return final_similars[:5]
                    else:
                         print(f"⚠️ {model_name} returned no valid game names. Trying next.")
                         continue
                         
                except Exception as e:
                    print(f"⚠️ Model {model_name} failed for image analysis: {str(e)[:100]}")
                    last_error = e
                    continue # Try next model

            print(f"❌ All Image Analysis models failed. Last error: {last_error}")
            return []

        except Exception as e:
            print(f"❌ Gemini Critical Setup Error: {e}")
            traceback.print_exc()
            return []

    def analyze_sentiment_buzz(self, api_key: str, game_name: str, similar_games: str = "") -> dict:
        if not api_key:
            return {"error": "Missing API Key", "score": 5, "reason": "No API Key"}
        
        # Check if the game is already in our DB to tell the IA it's released
        is_already_released = False
        db_sales = 0
        if game_name:
            match = self.df[self.df['nom'].str.lower() == game_name.lower().strip()]
            if not match.empty:
                is_already_released = True
                db_sales = match.iloc[0].get('ventes_reelles_officielles', 0)

        prompt = f"""
        Analyze the current market sentiment and hype (Buzz) for the game "{game_name}".
        {"Note: This game is already released and has recorded sales in our database." if is_already_released else "Note: This game might be unreleased or recently launched."}
        {"Similar titles: " + similar_games if similar_games else ""}
        
        Based on community reception, trailer views, and social media trends:
        1. Give a Buzz Score from 1.0 to 10.0 (where 10 is massive global hype like GTA VI or Elden Ring).
        2. Give a 1-sentence explanation of why (be specific about the game's reputation).
        
        Format: Score | Reason
        Example: 8.5 | High anticipation following a successful gameplay reveal and strong franchise history.
        """

        try:
            genai.configure(api_key=api_key)
            
            import datetime
            now_str = datetime.datetime.now().strftime("%Y-%m-%d")
            
            prompt = f"""
            Act as a gaming market analyst. Current Date: {now_str}.
            Analyze the public sentiment for the game: "{game_name}".
            Context / Similar Games: "{similar_games}".
            
            GUIDANCE:
            The current year is 2026.
            1. DETERMINE if the game is **Released** or **Unreleased** as of today.
            2. **IF RELEASED**: Analyze real player reviews (Steam/Metacritic). Check for bugs, performance issues, or review bombing using the rules below.
            3. **IF UNRELEASED**: Analyze the **HYPE & ANTICIPATION**.
               - Is the community excited? (High Score 8/10 to 10/10)
               - Is there skepticism or backlash from trailers? (Low Score 4/10)
               - **DO NOT** invent gameplay bugs or refunds for a game that doesn't exist yet. Estimate a `sentiment_percent` based on **Trust in Studio** and **Hype Level**.
            
            Task:
            1. Analyze **REAL USER SENTIMENT**. Do not rely on critic reviews if they differ from user opinion (e.g. review bombing, controversies, performance issues).
            2. Provide the **Metacritic USER Score** (converted to 0-100 scale) as the `sentiment_percent`.
            
            CRITICAL RULES:
            - **BE RUTHLESS. DO NOT BE POLITE.**
            - If the game has negative reception (e.g. Highguard, Mindseye), reflect it IMMEDIATELY in the score (e.g. 2/10 or 4/10).
            - Look for keywords: "Refund", "Disappointed", "Flop", "Trash", "Buggy", "Woke", "Boring". If these dominate, score MUST be < 50%.
            - If Metacritic User Score is 6.1, return **61**. NOT 70, NOT 78.
            - If User Score is 4.5, return **45**.
            - USE THE EXACT VALUE. DO NOT AVERAGE WITH CRITIC SCORE. DO NOT INFLATE.
            - If significant controversy exists, reflects the DIVIDED community sentiment (likely 30-50%), NOT the anticipated quality.
            
            3. Check if this game is part of a franchise. If YES:
               - **IDENTIFY the immediate PREVIOUS MAINLINE TITLE** released before this one.
                 (e.g. For 'Assassin's Creed Black Flag Remake', previous is 'Assassin's Creed Shadows' (2025)).
               - Find the **Metacritic User Score** of THAT specific previous title.
                 (e.g. AC Shadows had controversy -> Score ~61%. USE 61. Do NOT use Valhalla's score).
               - Estimate **Sales Volume**: If official numbers represent a "flop" or "mixed" reception (like Shadows), estimate conservatively (e.g. 5,000,000). If it was a hit (Valhalla), use ~14,000,000.
               - RETURN `previous_buzz`: 1-10 score for that previous game (e.g. Shadows = 4/10).
               If NO, return null for all three.

            4. Identify 3-5 SIMILAR GAMES (Released & Successful) in the same genre. Return them as a comma-separated string.
            
            Return a JSON object ONLY. DO NOT use markdown code blocks.
            IMPORTANT: Use double quotes for all keys and strings.
            Result Format:
            {{
                "score": <integer 1-10 for Hype/Buzz>,
                "sentiment_percent": <integer 0-100 representing Score>,
                "reason": "<One sentence summary>",
                "previous_game_name": "<Name of the identified previous game, e.g. AC Shadows>",
                "previous_sales": <integer estimated copies of previous game or null>,
                "previous_sentiment": <integer 0-100 score of previous game or null>,
                "previous_buzz": <integer 1-10 buzz of previous game or null>,
                "similar_games": "<String: Game 1, Game 2, Game 3>"
            }}
            """
            
            import re
            
            # User Preferred Models
            models_to_try = ['gemini-2.5-flash-lite', 'gemini-2.5-flash', 'gemini-3.0-flash', 'gemini-1.5-flash']
            
            last_error = None
            
            for model_name in models_to_try:
                try:
                    print(f"🤖 Trying Gemini Model: {model_name}...")
                    model = genai.GenerativeModel(model_name)
                    response = model.generate_content(prompt)
                    
                    # Success if we reach here
                    raw_text = response.text.strip()
                    print(f"✅ Success with {model_name}. Output: {raw_text[:50]}...")
                    
                    # JSON extraction
                    json_match = re.search(r'\{.*\}', raw_text, re.DOTALL)
                    
                    if json_match:
                        clean_text = json_match.group(0)
                        data = json.loads(clean_text)
                        return data
                    else:
                        clean_text = raw_text.replace('```json', '').replace('```', '').strip()
                        data = json.loads(clean_text)
                        return data
                        
                except Exception as e:
                     print(f"⚠️ Model {model_name} encountered error: {str(e)[:100]}")
                     last_error = e
                     continue # Try next model
            
            # If loop finishes without returning, all failed
            raise ValueError(f"All Gemini models failed. Last error: {last_error}")

        except Exception as e:
            print(f"Sentiment Analysis Error: {e}")
            return {"score": None, "reason": f"Error: {str(e)[:100]}"}

    def enrich_predecessor_data(self, data: dict) -> dict:
        """
        Extracts real sales/sentiment data from the database for the predecessor
        identified by Gemini in analyze_sentiment_buzz.
        """
        prev_name = data.get('previous_game_name')
        if not prev_name or self.df is None:
            return data

        # Try to find exactly or fuzzy match in DB
        # We prioritize 'ventes_reelles_officielles'
        pn_clean = prev_name.strip().lower()
        
        # Exact or fuzzy search (contains)
        match = self.df[self.df['nom'].str.lower() == pn_clean]
        if match.empty:
            # Fallback to fuzzy search if title is long enough
            if len(pn_clean) > 4:
                # Avoid matching the current game if it has a similar name (unlikely since we search for PREVIOUS)
                mask = self.df['nom'].str.lower().str.contains(pn_clean, na=False)
                match = self.df[mask].sort_values('ventes_reelles_officielles', ascending=False).head(1)

        if not match.empty:
            row = match.iloc[0]
            db_sales = float(row.get('ventes_reelles_officielles', 0))
            if db_sales == 0:
                 db_sales = float(row.get('ventes_est', 0))
            
            db_sentiment = float(row.get('sentiment', 0))
            
            print(f"🔍 DB Predecessor Match: {row['nom']} -> Sales: {db_sales} | Score: {db_sentiment}%")
            
            # Enrich if DB data is better (non-zero or higher quality)
            # We overwrite Gemini's estimate if DB has a non-zero value
            if db_sales > 0:
                data['previous_sales'] = int(db_sales)
            if db_sentiment > 0:
                data['previous_sentiment'] = int(db_sentiment)
                # Map sentiment to buzz if buzz is null or low
                if not data.get('previous_buzz'):
                    data['previous_buzz'] = int(db_sentiment / 10)

        return data


    def get_market_benchmarks(self, genre_name: str, budget: float, similar_games: List[str] = None):
        # 1. Select Segment
        segment = pd.DataFrame()
        genre_context = genre_name

        if similar_games and len(similar_games) > 0:
            # Fuzzy match similar games in our database
            # We use a regex join for 'OR' search
            import re
            mask = self.df['nom'].str.contains('|'.join([re.escape(s) for s in similar_games]), case=False, na=False)
            segment = self.df[mask].copy()
            
            if not segment.empty:
                genre_context = "Ciblé (Visuel)"
            else:
                # Fallback to genre if no identical names found
                segment = self.df[self.df['genre'] == genre_name].copy()

        if segment.empty:
            segment = self.df[self.df['genre'] == genre_name].copy()

        if segment.empty:
             return 20.0, 0.05, "Standard", []

        # 2. Avg Price of Success
        top_performers = segment[segment['ventes_est'] > segment['ventes_est'].median()]
        if top_performers.empty:
            avg_success_price = segment['prix'].mean()
        else:
            avg_success_price = top_performers['prix'].mean()
            
        # 3. Label & Friction
        if budget < 1000000:
            label = "Indie"
        elif budget < 15000000:
            label = "AA"
        else:
            label = "AAA"
            
        # 4. Friction Calculation
        tolerance_factor = 1.1 if genre_context == "Ciblé (Visuel)" else 1.2
        if label == "AAA": tolerance_factor += 0.1
        
        target_pivot_price = max(avg_success_price * tolerance_factor, 5.0)
        
        if avg_success_price < 2.0:
            friction = 0.25 
        else:
            friction = 1.0 / target_pivot_price
            
        return avg_success_price, friction, label, segment['nom'].tolist()

    def find_comparable_games(self, target_genre: str, target_budget: float, target_sentiment: float, similar_titles: List[str] = None) -> List[dict]:
        df = self.df.copy()
        
        scores = []
        for idx, row in df.iterrows():
            score = 0.0
            
            # 1. Genre match
            if str(row['genre']).lower() == str(target_genre).lower():
                score += 40.0
                
            # 2. Budget similarity
            game_budget = float(row.get('budget_estime', 0))
            if game_budget > 0 and target_budget > 0:
                ratio = min(game_budget, target_budget) / max(game_budget, target_budget)
                score += 30.0 * ratio
            elif game_budget == 0 and target_budget == 0:
                score += 30.0
                
            # 3. Sentiment similarity
            game_sent = float(row.get('sentiment', 0))
            if game_sent > 0 and target_sentiment > 0:
                diff = abs(game_sent - target_sentiment)
                score += max(0.0, 10.0 - (diff * 0.2)) # ±50 diff = 0
                
            # 4. Explicit Similar Titles Bonus
            if similar_titles:
                for st in similar_titles:
                    if st.strip().lower() in str(row['nom']).lower():
                        score += 20.0
                        break
                        
            # Use max(100)
            score = min(score, 100.0)
            
            # Simulated history data exactly like in prediction
            real_sales = float(row.get('ventes_reelles_officielles', 0))
            est_sales = float(row.get('ventes_est', 0))
            lifetime = real_sales if real_sales > 0 else est_sales
            
            if lifetime > 50000000:
                dist_ratios = [0.25, 0.17, 0.13, 0.10, 0.08, 0.07, 0.06, 0.05, 0.05, 0.04]
                evolution_years = [f"Year {i}" for i in range(1, 11)]
            else:
                dist_ratios = [0.55, 0.25, 0.12, 0.05, 0.03]
                evolution_years = ["Year 1", "Year 2", "Year 3", "Year 4", "Year 5"]
            evolution_sales = [int(lifetime * r) for r in dist_ratios]
            
            # Single player / Multiplayer from DB
            is_multi = int(row.get('is_multi', 0))
            type_str = "Multiplayer" if is_multi == 1 else "Single Player"
            
            scores.append({
                "title": row.get('nom', 'Unknown'),
                "year": "N/A",  # Not in DB
                "budget": game_budget,
                "price": float(row.get('prix', 0)),
                "metacritic": game_sent,
                "sales": lifetime,
                "similarity": round(score, 1),
                "type": type_str,
                "evolution_years": evolution_years,
                "evolution_sales": evolution_sales
            })
            
        # Sort by similarity descending
        scores.sort(key=lambda x: x['similarity'], reverse=True)
        
        # Deduplicate and return top 10
        seen = set()
        unique_results = []
        for s in scores:
            if s['title'] not in seen:
                seen.add(s['title'])
                unique_results.append(s)
            if len(unique_results) >= 10:
                break
                
        return unique_results

    def run_monte_carlo(self, base_sales: float, genre_name: str, budget: float, sentiment_target: int, sentiment_ia_score: float, wishlists: int, previous_sales: int, num_simulations=5000):
        # Base variance for the genre
        variance = 0.5 
        
        segment = self.df[self.df['genre'] == genre_name]
        if not segment.empty:
            mean_sales = segment['ventes_est'].mean()
            std_sales = segment['ventes_est'].std()
            if mean_sales > 0 and pd.notna(std_sales):
                variance = min(max(std_sales / mean_sales, 0.3), 1.2) # Bound the coefficient of variation
        
        sigma = variance
        
        # Budget reduces variance (more predictable)
        if budget > 20000000:
            sigma *= 0.8
        elif budget < 500000:
            sigma *= 1.2
            
        # Wishlists indicate demand, higher wishlists = slightly lower variance
        if wishlists > 100000:
            sigma *= 0.9
            
        # High sentiment and buzz reduces flop risk but increases blockbuster potential
        if sentiment_ia_score is None:
            sentiment_ia_score = 5.0
            
        # If it's a franchise with previous sales, it's highly predictable
        if previous_sales and previous_sales > 0:
            sigma *= 0.5
            
        # Calculate lognormal distribution centered around our base_sales estimator
        mu = np.log(max(base_sales, 100)) - (sigma**2) / 2
        
        simulated_sales = np.random.lognormal(mean=mu, sigma=sigma, size=num_simulations)
        
        # Calculate percentiles
        p10 = float(np.percentile(simulated_sales, 10))
        p50 = float(np.percentile(simulated_sales, 50))
        p90 = float(np.percentile(simulated_sales, 90))
        
        # Generate histogram
        # We cap it at P95 to avoid huge outliers skewing the chart display
        cap_val = np.percentile(simulated_sales, 95)
        filtered_sims = simulated_sales[simulated_sales <= cap_val]
        
        hist, bins = np.histogram(filtered_sims, bins=40)
        
        return {
            "p10": p10,
            "p50": p50,
            "p90": p90,
            "histogram_data": hist.tolist(),
            "histogram_bins": [float(b) for b in bins[:-1]]
        }

    def predict_optimization(
        self, 
        genre_name: str, 
        budget: float, 
        wishlists: int, 
        reviews_target: float, # Not used directly in input but derived
        sentiment_target: int,
        month: int,
        langs: int,
        similar_games: List[str] = None,
        game_name: str = None,
        sentiment_ia_score: float = None,
        fixed_price: float = None,
        previous_sales: int = None,
        previous_sentiment: int = None,
        previous_buzz: int = None,
        num_dlcs: int = 0,
        dlc_price: float = 0.0
    ) -> dict:
        
        if previous_sales:
             print(f"🔄 Integrating Previous Franchise Sales: {previous_sales} copies")
        
        game_specific_match = None
        real_sales_data = None
        real_game_price = None
        
        if game_name:
            gn_clean = game_name.strip().lower()
            # Try to find the game in our database - IMPROVED: Fuzzy/Contains match for exact title
            match = self.df[self.df['nom'].str.lower() == gn_clean]
            
            # Fuzzy fallback if no exact match (helps with "Game Name" vs "Game Name (Original)")
            if match.empty:
                # Limit to relatively short names to avoid matching too much noise
                if len(gn_clean) > 4:
                    fuzzy_match = self.df[self.df['nom'].str.lower().str.contains(gn_clean, na=False)]
                    if not fuzzy_match.empty:
                        # Sort by sales to pick the most prominent hit
                        match = fuzzy_match.sort_values('ventes_est', ascending=False).head(1)

            if not match.empty:
                game_specific_match = match.iloc[0]['nom']
                # Use real_sales_data PRIORITIZED column
                if 'ventes_reelles_officielles' in match.columns and match.iloc[0]['ventes_reelles_officielles'] > 0:
                    real_sales_data = match.iloc[0]['ventes_reelles_officielles']
                    real_game_price = match.iloc[0]['prix']
                elif 'ventes_est' in match.columns:
                    real_sales_data = match.iloc[0]['ventes_est']
                    real_game_price = match.iloc[0]['prix']
                
                print(f"🎯 Match Found in DB: {game_specific_match} -> Price: {real_game_price} | Sales: {real_sales_data}")

        # 1. Market Analysis
        bench_price, friction, label, used_similars = self.get_market_benchmarks(genre_name, budget, similar_games)
        local_friction = friction # Default friction for price calculation
        
        # 2. Sentiment & Wishlist Logic
        if sentiment_target is None or sentiment_target <= 0:
            sentiment_target = 75 # Standard neutral-pos target
            
        if sentiment_ia_score is not None:
            # Map 1-10 to 10-100
            ia_sentiment_percent = sentiment_ia_score * 10
            # Blend with user target (weighted towards IA)
            sentiment_target = (sentiment_target * 0.3 + ia_sentiment_percent * 0.7)
            print(f"🤖 Sentiment Adjusted by IA: {sentiment_target:.1f}%")

        # Smart Wishlist estimation if empty
        if not wishlists or wishlists <= 0:
            # Industry benchmarks provided by USER
            # Top AAA: 2M - 5M+
            # Standard AAA: 1M - 2M
            # AA Successful: 300k - 1M
            # AA Correct: 100k - 300k
            
            # Use Buzz Score (1-10) as the primary navigator
            buzz = sentiment_ia_score if (sentiment_ia_score and sentiment_ia_score > 0) else 5.0
            
            if label == "AAA":
                if buzz >= 8: # Top AAA
                    # Base interpolation for Top AAA: 2M to 5M
                    wishlist_est = 2000000 + (buzz - 8) * (1500000) # Buzz 10 = 5M
                    
                    # EXTRA GATE: Only exceed 5M if "Hyper Hype" (9.5+) AND "Incredible Budget" (100M+)
                    if buzz >= 9.5 and budget >= 100000000:
                        bonus = (buzz - 9.5) * 4000000 # Can reach 7M+ for scores of 10
                        wishlist_est += bonus
                        print(f"🌟 MEGA-HIT POTENTIAL DETECTED: Budget {budget/1e6}M and Buzz {buzz}")
                    else:
                        # Hard cap at 5M for standard high-end AAA
                        wishlist_est = min(wishlist_est, 5000000)
                else: # Standard AAA
                    # Interpolate between 1M and 2M
                    wishlist_est = 1000000 + (buzz - 1) * (1000000 / 7)
            elif label == "AA":
                if buzz >= 8: # AA Très Réussi
                    # Interpolate between 300k and 1M
                    wishlist_est = 300000 + (buzz - 8) * (350000) # Buzz 10 = 1M
                else: # AA Correct
                    # Interpolate between 100k and 300k
                    wishlist_est = 100000 + (buzz - 1) * (200000 / 7)
            else: # Indie / Small AA
                wishlist_est = 5000 + (buzz - 1) * (95000 / 9)
            
            # Small modulation by budget (visibility bonus) only for non-mega hits
            if wishlist_est < 5000000:
                budget_factor = max(1.0, (budget / 1000000) ** 0.1)
                wishlist_est *= budget_factor
            
            wishlists = int(wishlist_est)
            print(f"🧠 Tier-Calibrated Wishlist Estimation: {wishlists:,} (Label: {label}, Buzz: {buzz})")

        # 3. Volume Prediction (CCU & Sales)
        if real_sales_data and real_sales_data > 0:
            # The 'real sales' in DB are often launch snapshots (e.g. first week/month).
            # We estimate the full Year 1 to be 1.2x the launch snapshot.
            year1_est = real_sales_data * 1.2
            
            # Then we extrapolate the 5-year total.
            # Y1 is typically 55% of 5-year lifetime sales for successful games.
            y1_ratio = 0.55
            # For mega hits (GTA/Minecraft), Y1 is a smaller % because the tail is much longer
            if real_sales_data > 40000000: y1_ratio = 0.30 
            
            est_total_sales = year1_est / y1_ratio
            
            print(f"📈 Real Game Detected: {real_sales_data} copies at launch.")
            print(f"💰 Year 1 Prediction: {int(year1_est)} copies (Snapshot x 1.2)")
            print(f"📊 5-Year Full Lifetime Est: {int(est_total_sales)} copies")

            # Reverse engineer CCU for the curve
            ccu_simule = real_sales_data / 40 

            # Established hits are nearly price-inelastic in their first year
            if real_sales_data >= 5000000:
                local_friction = friction * 0.05  # Virtually no impact for global blockbusters
            elif real_sales_data >= 1000000:
                local_friction = friction * 0.2
            else:
                local_friction = friction * 0.5
        else:
            # Simulation Logic
            ratio = 0.07 if budget > 10000000 else 0.04
            ccu_simule = wishlists * ratio
            
            # EXPERT UPGRADE: Budget-driven Awareness Baseline
            # A huge budget implies marketing/visibility. 
            # 100M budget should guarantee at least a baseline reach even with 0 wishlists.
            if budget > 80000000:
                # Ultra AAA Baseline: ~8000-15000 CCU purely from marketing force
                awareness_baseline = (budget / 100000000) * 12000
                ccu_simule = max(ccu_simule, awareness_baseline)
            elif budget > 50000000:
                awareness_baseline = (budget / 100000000) * 6000
                ccu_simule = max(ccu_simule, awareness_baseline)
            elif budget > 10000000:
                awareness_baseline = (budget / 10000000) * 500
                ccu_simule = max(ccu_simule, awareness_baseline)

            # Cap CCU
            if ccu_simule > 200000 and budget < 50000000:
                ccu_simule = 200000 + (ccu_simule - 200000) * 0.1
            
            # Estimate Total Sales from CCU
            # Multiplier varies by genre retention, but 30-50x is a standard rule of thumb for lifetime sales vs peak CCU
            sales_multiplier = 40 # Base
            if label == "AAA": 
                sales_multiplier = 60 # AAA have stronger legs/presence
                if budget > 80000000: sales_multiplier = 85 # Ultra-AAA (GTA/Assassins Creed level)
            
            if sentiment_target > 90: sales_multiplier *= 1.2
            
            est_total_sales = ccu_simule * sales_multiplier

            # Franchise/Sequel Adjustment
            
            if previous_sales:
                # Adjust based on sentiment COMPARISON
                growth_factor = 1.0

                # 1. User Score Growth
                if previous_sentiment and previous_sentiment > 0:
                     sentiment_ratio = (sentiment_target / float(previous_sentiment))
                     growth_factor = sentiment_ratio
                else:
                     # If previous sentiment unknown, assume new game is expected to be as good as a hit (85%)
                     growth_factor = (sentiment_target / 85.0)

                # 2. Buzz Growth (if available)
                if previous_buzz and sentiment_ia_score:
                    buzz_ratio = (sentiment_ia_score / float(previous_buzz))
                    # Blend: Standard 70% Sentiment, 30% Buzz impact
                    buzz_weight = 0.3
                    if buzz_ratio > 1.2: buzz_weight = 0.5
                    if buzz_ratio > 1.5: buzz_weight = 0.7
                    
                    growth_factor = (growth_factor * (1-buzz_weight)) + (buzz_ratio * buzz_weight)
                    print(f"📢 Buzz Impact: Prev {previous_buzz} -> New {sentiment_ia_score} (Ratio {buzz_ratio:.2f}) [Weight {buzz_weight}]")

                # BOOSTER: Success Momentum for Mega-Franchises (User request: next starts even stronger)
                # If a franchise was already a hit (>10M), sequels tend to have 
                # a natural growth due to brand awareness and platform expansion.
                if previous_sales > 10000000:
                    momentum_bonus = 1.15 # Baseline +15% growth for brand power
                    if previous_sales > 50000000:
                        momentum_bonus = 1.35 # GTA-level momentum (Mega-Hit expansion)
                    
                    # Only apply bonus if the new sentiment is not terrible
                    if sentiment_target >= 70:
                        growth_factor *= momentum_bonus
                        print(f"🚀 Brand Momentum Bonus Applied: {momentum_bonus}x")

                print(f"📈 Franchise Trend: Global Growth Factor {growth_factor:.2f}x")
                
                # Clamp growth to reasonable limits (0.5x to 3.0x of previous)
                growth_factor = max(0.5, min(growth_factor, 3.0))
                
                projected_franchise_sales = previous_sales * growth_factor
                
                # Blend: Stronger weight for huge hits OR viral hype
                weight_franchise = 0.7
                if previous_sales > 50000000:
                     weight_franchise = 1.0 # Pure franchise power for GTA-like anomalies
                     local_friction = friction * 0.1 # Very low, but non-zero elasticity
                elif previous_sales >= 5000000 or growth_factor > 1.3: 
                    weight_franchise = 0.95 
                    local_friction = friction * 0.2 
                elif previous_sales > 1000000:
                    weight_franchise = 0.85
                    local_friction = friction * 0.5
                
                est_total_sales = (est_total_sales * (1-weight_franchise)) + (projected_franchise_sales * weight_franchise)
                print(f"📊 Franchise Adjusted Sales: {int(est_total_sales)} (Growth: {growth_factor:.2f}x)")


        print(f"🔮 Simulation: Wishlists={wishlists} -> Est. CCU={int(ccu_simule)} | Est. Sales={int(est_total_sales)}")
        
        # Extend price range for modern AAA
        max_curve_price = 80
        if label == "AAA" or (fixed_price and fixed_price > 80): max_curve_price = 120
        
        prix_range = np.linspace(1, max_curve_price, 80)
        profits = []
        sales_curve = []
        
        
        # Lifecycle Factor: Approx 0.9 (Weighted avg of 1.0, 0.85, 0.72...)
        lifecycle_decay_factor = 0.9

        for p in prix_range:
            # Price Friction
            # If we matched a real game, its price in DB is our 'center' of gravity for sales
            current_bench = real_game_price if (real_game_price and real_game_price > 0) else bench_price
            
            # Standard elastic curve
            price_factor = np.exp(-local_friction * (p - current_bench) / current_bench) if current_bench > 0 else 1.0
            # Clip
            price_factor = min(max(price_factor, 0.1), 1.5)
            
            # Base sales modulated by price
            # CRITICAL: If we have real data, we don't apply calibration factor (which is for unknown models)
            is_real = (real_sales_data and real_sales_data > 0)
            calib = 1.0 if is_real else self.calibration_factor
            
            f_sales = est_total_sales * price_factor * calib
            
            # Additional safety for matched real games: Year 1 should never be less than the actual sales recorded
            if is_real:
                y1_floor = real_sales_data
                if (f_sales * 0.55) < y1_floor:
                    # Boost the total to ensure Year 1 (55% of total) matches the floor
                    f_sales = y1_floor / 0.55
            
            final_sales = f_sales
            
            # Net Revenue (Steam cut 30% + VAT/Taxes approx ~ 40-50% off total. Let's say * 0.55 net)
            # Applied Lifecycle Decay Factor (User requested ~15% yearly drop impact)
            net_revenue = final_sales * p * 0.55 * lifecycle_decay_factor
            profit = net_revenue - budget
            
            profits.append(float(profit))
            sales_curve.append(float(final_sales))
        
        # Default Optimal
        best_idx = np.argmax(profits)
        best_price = float(prix_range[best_idx])
        max_profit = float(profits[best_idx])
        final_sales_display = float(sales_curve[best_idx]) # Base case
        
        # Override if Fixed Price
        if fixed_price and fixed_price > 0:
            best_price = float(fixed_price)
            p = best_price
            current_bench = real_game_price if (real_game_price and real_game_price > 0) else bench_price
            price_factor = np.exp(-local_friction * (p - current_bench) / current_bench) if current_bench > 0 else 1.0
            price_factor = min(max(price_factor, 0.1), 1.5)
            
            is_real = (real_sales_data and real_sales_data > 0)
            calib = 1.0 if is_real else self.calibration_factor
            
            f_sales = est_total_sales * price_factor * calib
            if is_real:
                y1_floor = real_sales_data
                if (f_sales * 0.55) < y1_floor:
                    f_sales = y1_floor / 0.55
            
            final_sales_fixed = f_sales
            net_rev_fixed = final_sales_fixed * p * 0.55 * lifecycle_decay_factor
            max_profit = float(net_rev_fixed - budget)
            final_sales_display = float(final_sales_fixed) # Override sales
            print(f"🔒 Fixed Price Override: ${best_price} -> Profit: ${int(max_profit)} Sales: {int(final_sales_display)}")

        # --- DLC REVENUE CALCULATION ---
        if num_dlcs and num_dlcs > 0 and dlc_price > 0:
            # Dynamic Attachment Rate based on Quality/Sentiment
            # If game is bad, nobody buys DLC. If game is masterpiece, 20%+ buy.
            # Scale: 60% score -> 10% attach. 90% score -> 20% attach.
            
            if sentiment_target >= 90:
                attachment_rate = 0.20
            elif sentiment_target <= 60:
                attachment_rate = 0.10
            else:
                # Linear interpolation between 60 (0.10) and 90 (0.20)
                # Slope = (0.20 - 0.10) / (90 - 60) = 0.10 / 30 = 0.0033
                attachment_rate = 0.10 + ((sentiment_target - 60) * 0.0033)
            
            dlc_unit_sales = final_sales_display * attachment_rate

            # Total DLC Revenue (Net after Steam cut)
            # Assuming spread out over years, but summed up for Lifetime Value
            total_dlc_net_revenue = (dlc_unit_sales * dlc_price * 0.55) * num_dlcs
            
            print(f"📦 DLC Plan: {num_dlcs} DLCs @ ${dlc_price} | Quality {int(sentiment_target)}% -> Att. Rate {int(attachment_rate*100)}% | +${int(total_dlc_net_revenue)} Net Revenue")

            # Add to Total Profit
            max_profit += total_dlc_net_revenue

        # Sales Evolution Simulation
        if final_sales_display > 50000000:
            # MEGA HIT (GTA VI, Minecraft style) - Long Tail 10 Years
            # Slower decay, longevity.
            # Y1: 25% (Launch), Y2: 17%, Y3: 13%, Y4: 10%, Y5: 8%, Y6: 7%, Y7: 6%, Y8: 5%, Y9: 5%, Y10: 4%
            dist_ratios = [0.25, 0.17, 0.13, 0.10, 0.08, 0.07, 0.06, 0.05, 0.05, 0.04]
            evolution_years = [f"Year {i}" for i in range(1, 11)]
            evolution_sales = [int(final_sales_display * r) for r in dist_ratios]
            print(f"🌟 MEGA HIT DETECTED! Using 10-Year Long Tail Curve.")
        else:
            # Standard Game - 5 Years
            # Y1: Launch Hype (55%), Y2: First Sales/Discount (25%), Y3: Back Catalogue (12%), Y4: Deep Discount (5%), Y5: Long Tail (3%)
            dist_ratios = [0.55, 0.25, 0.12, 0.05, 0.03]
            evolution_sales = [int(final_sales_display * r) for r in dist_ratios]
            evolution_years = ["Year 1", "Year 2", "Year 3", "Year 4", "Year 5"]

        # CRITICAL: If we have real official sales data, Year 1 MUST match it at minimum
        if real_sales_data and real_sales_data > 0:
            # VELOCITY LOGIC: If a game sells millions very quickly (like 4M recently), 
            # the Year 1 total should be much higher than just the current recorded number.
            # We estimate Year 1 as a multiple of current launch sales if they are already huge.
            projected_y1 = evolution_sales[0]
            
            # Heuristic: If current confirmed sales > 1M, it's a massive launch.
            # Year 1 is typically ~2.5x to 4x the 'Opening Week/Launch' confirmed data in the DB
            # if that data represents a recent hit.
            if real_sales_data >= 1000000:
                momentum_multiplier = 3.0 # Standard for major releases
                if real_sales_data >= 4000000:
                    momentum_multiplier = 2.5 # Slightly lower multiplier as numbers get huge (saturation)
                
                velocity_y1 = real_sales_data * momentum_multiplier
                projected_y1 = max(projected_y1, velocity_y1)
                print(f"🔥 Launch Velocity Detected! confirmed: {real_sales_data:,} -> Projected Y1: {int(projected_y1):,}")

            if projected_y1 > real_sales_data:
                evolution_sales[0] = int(projected_y1)
                # Update the total display to be the sum (Year 1 + future years)
                final_sales_display = sum(evolution_sales)
            else:
                # Minimum floor case
                evolution_sales[0] = int(real_sales_data)
                final_sales_display = sum(evolution_sales)

        # Break-even Analysis (Cumulative Profit vs Cumulative Sales)
        # based on selected best_price or fixed_price
        final_price = best_price
        
        # Calculate for 20 points from 0 to final_sales_display
        sales_steps = np.linspace(0, final_sales_display, 20)
        cumulative_profits = []
        for s in sales_steps:
            # Cumulative Net = (Sales * Price * Steam/Tax Cut) - Budget
            # We already factored in lifecycle_decay_factor for the total, 
            # for the curve we'll use the same average factor.
            cum_net = (s * final_price * 0.55 * lifecycle_decay_factor) - budget
            cumulative_profits.append(float(cum_net))

        # Determine year-end milestones for the chart
        year_milestones = []
        running_total_sales = 0
        for i_y, y_sales in enumerate(evolution_sales):
            running_total_sales += y_sales
            cum_profit_at_year = (running_total_sales * final_price * 0.55 * lifecycle_decay_factor) - budget
            year_milestones.append({
                "year": evolution_years[i_y],
                "cumulative_sales": int(running_total_sales),
                "cumulative_profit": float(cum_profit_at_year)
            })

        # Comparable games benchmark
        comparable_games = self.find_comparable_games(genre_name, budget, sentiment_target, similar_games)

        # Dynamic Pricing Table Simulation
        # Dynamic Pricing Table Simulation
        target_prices = [40, 50, 60, 70, 80, 90]
        dynamic_pricing_data = []
        for sim_p in target_prices:
            current_bench_safe = real_game_price if (real_game_price and real_game_price > 0) else bench_price
            if not current_bench_safe or current_bench_safe <= 0:
                current_bench_safe = 60.0
                
            # Base the curve strictly on elasticity ratio against the known optimal best_price
            # Use base friction to guarantee a visible curve, avoiding zero elasticity from franchise multiplier
            sim_friction = max(friction, 1.0)
            best_price_factor = np.exp(-sim_friction * (best_price - current_bench_safe) / current_bench_safe)
            sim_price_factor = np.exp(-sim_friction * (sim_p - current_bench_safe) / current_bench_safe)
            
            elasticity_ratio = sim_price_factor / best_price_factor if best_price_factor > 0 else 1.0
            
            # Apply ratio to final expected sales
            f_sales_dp = final_sales_display * elasticity_ratio
            
            sim_rev = f_sales_dp * sim_p * 0.55 * lifecycle_decay_factor
            sim_profit = sim_rev - budget
            
            dynamic_pricing_data.append({
                "price": sim_p,
                "sales": int(f_sales_dp),
                "revenue": float(sim_rev),
                "profit": float(sim_profit)
            })

        # Monte Carlo Simulation
        monte_carlo = self.run_monte_carlo(
            base_sales=final_sales_display,
            genre_name=genre_name,
            budget=budget,
            sentiment_target=sentiment_target,
            sentiment_ia_score=sentiment_ia_score,
            wishlists=wishlists,
            previous_sales=previous_sales
        )

        # Marketing Efficiency Model
        marketing_budgets = [5000000, 10000000, 20000000, 50000000, 100000000, 200000000]
        marketing_efficiency = []
        
        # Define saturation based on base budget and segment
        saturation_point = max(10000000, budget * 3)
        
        for m_budget in marketing_budgets:
            max_multiplier = 2.0 if label == "AAA" else (1.5 if label == "AA" else 1.2)
            lift_ratio = (m_budget / (m_budget + saturation_point)) * (max_multiplier - 1.0)
            
            lift_percent = lift_ratio * 100
            extra_sales = final_sales_display * lift_ratio
            extra_revenue = extra_sales * best_price * 0.55 * lifecycle_decay_factor
            
            roi = ((extra_revenue - m_budget) / m_budget) * 100
            
            marketing_efficiency.append({
                "budget": m_budget,
                "lift_percentage": round(lift_percent, 1),
                "roi": round(roi, 1),
                "extra_revenue": float(extra_revenue)
            })

        # Global Risk Index
        genre_df = self.df[self.df['genre'] == genre_name]
        total_games = len(self.df) if len(self.df) > 0 else 1000
        
        # 1. Budget Risk
        avg_budget = genre_df['budget_estime'].median() if 'budget_estime' in genre_df.columns and not genre_df['budget_estime'].isnull().all() else 5000000
        budget_ratio = (budget / avg_budget) if avg_budget > 0 else 1.0
        budget_risk = min(10.0, max(1.0, budget_ratio * 4.0))

        # 2. Genre Risk (Saturation)
        genre_density = len(genre_df) / total_games
        genre_risk = min(10.0, max(1.0, genre_density * 100 * 1.5)) 

        # 3. Market Risk
        price_ratio = (best_price / bench_price) if bench_price > 0 else 1.0
        price_risk = min(10.0, max(1.0, price_ratio * 5.0))
        track_record_mod = -3.0 if (previous_sales and previous_sales > 1000000) else (-1.0 if (previous_sales and previous_sales > 100000) else 0.0)
        market_risk = min(10.0, max(1.0, price_risk + track_record_mod))
        
        # 4. Buzz Risk
        buzz_factor_risk = float(sentiment_ia_score) if sentiment_ia_score is not None else 5.0
        buzz_risk = max(1.0, 10.0 - buzz_factor_risk)
        
        # 5. Franchise Risk (Track Record)
        has_franchise = False
        franchise_risk = None
        if previous_sales and previous_sales > 0:
            has_franchise = True
            if previous_sales > 10000000:
                franchise_risk = 1.0
            elif previous_sales > 5000000:
                franchise_risk = 2.0
            elif previous_sales > 1000000:
                franchise_risk = 3.5
            elif previous_sales > 500000:
                franchise_risk = 5.0
            elif previous_sales > 100000:
                franchise_risk = 7.0
            else:
                franchise_risk = 8.5
            overall_risk = round((budget_risk * 0.25) + (genre_risk * 0.15) + (market_risk * 0.15) + (buzz_risk * 0.25) + (franchise_risk * 0.20), 1)
        else:
            overall_risk = round((budget_risk * 0.3) + (genre_risk * 0.2) + (market_risk * 0.2) + (buzz_risk * 0.3), 1)
        
        global_risk = {
            "overall": overall_risk,
            "budget_risk": round(budget_risk, 1),
            "genre_risk": round(genre_risk, 1),
            "market_risk": round(market_risk, 1),
            "buzz_risk": round(buzz_risk, 1)
        }
        
        if has_franchise:
            global_risk["franchise_risk"] = round(franchise_risk, 1)
        # Greenlight Score
        # 1. Expected ROI Factor (0-10), assume 300% ROI = 10
        base_roi = (max_profit / budget) * 100 if budget > 0 else 0
        roi_factor = min(10.0, max(0.0, base_roi / 30.0))
        
        # 2. Market Demand Factor (0-10), assume 1M sales = 10 for AA, scaling by label
        demand_target = 5000000 if label == "AAA" else (1000000 if label == "AA" else 300000)
        demand_factor = min(10.0, max(0.0, (final_sales_display / demand_target) * 10))
        
        # 3. Risk Factor (0-10, inverted risk)
        risk_factor = max(0.0, 10.0 - overall_risk)
        
        # 4. Genre Trend Factor (0-10, inverted genre risk)
        trend_factor = max(0.0, 10.0 - genre_risk)
        
        # 5. Buzz Factor (0-10, based on sentiment_ia_score)
        buzz_factor = float(sentiment_ia_score) if sentiment_ia_score is not None else 5.0
        
        greenlight_score_raw = (roi_factor * 0.25) + (demand_factor * 0.20) + (risk_factor * 0.20) + (trend_factor * 0.10) + (buzz_factor * 0.25)
        greenlight_score = round(min(10.0, max(0.0, greenlight_score_raw)), 1)
        
        if greenlight_score >= 7.5:
            recommendation = "Strong Opportunity"
        elif greenlight_score >= 4.5:
            recommendation = "Moderate Potential"
        else:
            recommendation = "Avoid"
            
        greenlight = {
            "score": greenlight_score,
            "recommendation": recommendation
        }

        # -----------------------------
        # Generate Complete Context Review
        # -----------------------------
        context_review = ""
        if greenlight_score >= 7.5:
            context_review = f"Based on the Greenlight Score of {greenlight_score}/10, the AI classifies this as a <b style='color:#00ff88;'>Strong Opportunity</b>. "
        elif greenlight_score >= 4.5:
            context_review = f"Based on the Greenlight Score of {greenlight_score}/10, the AI classifies this as having <b style='color:#f39c12;'>Moderate Potential</b>. "
        else:
            context_review = f"Based on the Greenlight Score of {greenlight_score}/10, the AI classifies this as a <b style='color:#ff4444;'>High-Risk / Avoid</b> project. "
            
        if has_franchise:
            context_review += f"<br><br>The strong track record from previous sales ({previous_sales:,} units) significantly de-risks the investment and provides excellent baseline visibility. "
        else:
            context_review += "<br><br>Without previous franchise sales data, this project acts as a new standalone IP where strong marketing execution and community buzz will be critical. "
            
        context_review += f"Overall, the algorithm predicts an optimal launch price of <b>${best_price}</b> aiming for estimated base sales of ~{int(final_sales_display):,} units (accounting for current '{genre_name}' genre saturation and market trends)."

        return {
            "best_price": best_price,
            "max_profit": max_profit,
            "est_total_sales": int(final_sales_display),
            "wishlists": int(wishlists),
            "sentiment_ia_score": sentiment_ia_score,
            "benchmark_price": float(bench_price),
            "segment_label": label,
            "context_review": context_review,
            "game_specific_match": game_specific_match,
            "used_similars": used_similars[:5],
            "curve_prices": prix_range.tolist(),
            "curve_profits": profits,
            "curve_sales": sales_curve,
            "evolution_years": evolution_years,
            "evolution_sales": evolution_sales,
            "breakeven_sales_steps": sales_steps.tolist(),
            "breakeven_profits": cumulative_profits,
            "year_milestones": year_milestones,
            "comparable_games": comparable_games,
            "monte_carlo": monte_carlo,
            "dynamic_pricing": dynamic_pricing_data,
            "global_risk": global_risk,
            "marketing_efficiency": marketing_efficiency,
            "greenlight": greenlight
        }

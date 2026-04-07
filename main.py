from fastapi import FastAPI, UploadFile, File, Form, Depends, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import List, Optional
import json
import uvicorn
import os
import bcrypt
import uuid
import resend
from supabase import create_client, Client
from ai_engine import GameRevenuePredictor

app = FastAPI()

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize AI Engine
CSV_PATH = os.path.join(os.path.dirname(__file__), "data", "base_donnees_jeux_expert_calibrated_v2.csv")
try:
    engine = GameRevenuePredictor(CSV_PATH)
    print(f"✅ AI Engine initialized successfully. CSV path: {CSV_PATH}")
except Exception as e:
    import traceback
    print(f"❌ CRITICAL ERROR initializing AI Engine from {CSV_PATH}")
    traceback.print_exc()
    engine = None

# --- DATABASE SETUP (SUPABASE) ---
SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "")

try:
    if SUPABASE_URL and SUPABASE_KEY:
        supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
        # Diagnostic: check key prefix (without revealing full key)
        key_start = SUPABASE_KEY[:6] if len(SUPABASE_KEY) > 6 else "---"
        is_service = "✅ (Service Role Key detected?)" if SUPABASE_KEY.startswith("eyJ") and len(SUPABASE_KEY) > 50 else "⚠️ (Short key: Anon?)"
        print(f"✅ Supabase client initialized. Key starts with: {key_start}... {is_service}")
        
        # Immediate Connection Test
        test = supabase.table('users').select('id').limit(1).execute()
        print(f"🔗 Database connection test: SUCCESS ({len(test.data)} user(s) found).")
    else:
        print("❌ Supabase credentials missing (URL or KEY) -> DB disabled")
        supabase = None
except Exception as e:
    print(f"❌ CRITICAL Supabase init error: {e}")
    supabase = None

# --- EMAIL HELPER (RESEND) ---
RESEND_API_KEY = os.environ.get("RESEND_API_KEY", "")
BASE_URL = os.environ.get("BASE_URL", "http://localhost:8000")

if RESEND_API_KEY:
    resend.api_key = RESEND_API_KEY

# --- GEMINI FALLBACK ---
GEMINI_DEFAULT_KEY = os.environ.get("GOOGLE_API_KEY", "")
if GEMINI_DEFAULT_KEY:
    print("✅ Default Gemini API Key detected (Environment).")
else:
    print("⚠️ No default Gemini Key found. Users will need to provide their own.")

async def send_email(to_email: str, subject: str, html_body: str):
    if not RESEND_API_KEY:
        print(f"⚠️ Resend API Key Missing. Would have sent to {to_email}: {subject}")
        return
    
    try:
        r = resend.Emails.send({
            "from": "no-reply@gamepredict.ai",
            "to": to_email,
            "subject": subject,
            "html": html_body
        })
        print(f"📧 Email sent via Resend: {r}")
    except Exception as e:
        print(f"❌ Failed to send email via Resend: {e}")

class SignupRequest(BaseModel):
    email: str
    password: str
    organization: str

class LoginRequest(BaseModel):
    email: str
    password: str

class LostPasswordRequest(BaseModel):
    email: str

class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str

class FeedbackRequest(BaseModel):
    comment: str
    user_email: str
    inputs: dict
    results: dict

class ContactRequest(BaseModel):
    full_name: str
    organisation: str
    email: str
    message: str

@app.post("/api/contact")
async def contact(req: ContactRequest):
    html_body = f"""
    <div style="font-family: 'Outfit', sans-serif; color: #333; line-height: 1.6; max-width: 600px; margin: 0 auto; border: 1px solid #eee; padding: 20px; border-radius: 10px;">
        <h2 style="color: #6c5ce7; border-bottom: 2px solid #6c5ce7; padding-bottom: 10px;">New Contact Us Message</h2>
        <p><strong>Full Name:</strong> {req.full_name}</p>
        <p><strong>Organisation:</strong> {req.organisation}</p>
        <p><strong>E-Mail:</strong> <a href="mailto:{req.email}">{req.email}</a></p>
        <hr style="border: 0; border-top: 1px solid #eee; margin: 20px 0;">
        <h3 style="color: #444;">Message:</h3>
        <p style="white-space: pre-wrap; background: #f9f9f9; padding: 15px; border-radius: 5px; border-left: 4px solid #6c5ce7;">{req.message}</p>
    </div>
    """
    
    await send_email("mickurt@gmail.com", f"Contact Us: {req.full_name} ({req.organisation})", html_body)
    return {"message": "Your message has been sent successfully."}

@app.post("/api/signup")
async def signup(req: SignupRequest):
    if not supabase:
        print("❌ CRITICAL: Supabase client is NOT initialized. Possible RLS or Private Key issue.")
        return JSONResponse(status_code=503, content={"message": "Database disconnected. Check Service Role Key."})
    
    email_normalized = req.email.lower().strip()
    
    # Check if user exists (case-insensitive check)
    res = supabase.table('users').select('id, email').ilike('email', email_normalized).execute()
    if len(res.data) > 0:
        return JSONResponse(status_code=400, content={"message": f"Email '{res.data[0]['email']}' already exists"})
    
    user_id = str(uuid.uuid4())
    token = str(uuid.uuid4())
    hashed = bcrypt.hashpw(req.password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    
    supabase.table('users').insert({
        'id': user_id,
        'email': email_normalized,
        'password': hashed,
        'organization': req.organization,
        'validation_token': token,
        'is_validated': 0
    }).execute()
    
    # Send email to Admin
    admin_body = f"""
    <h2>New Signup Request</h2>
    <p><b>Email:</b> {req.email}</p>
    <p><b>Organization:</b> {req.organization}</p>
    <p>Click the button below to validate this account and notify the user:</p>
    <a href="{BASE_URL}/api/validate/{token}" style="display:inline-block; margin-top:15px; margin-bottom:15px; background:#00ff88; color:black; padding:10px 20px; text-decoration:none; border-radius:5px; font-weight:bold;">VALIDATE ACCOUNT</a>
    """
    await send_email("mickurt@gmail.com", f"New Signup: {req.email}", admin_body)
    
    return {"message": "Signup successful. Waiting for admin validation."}

@app.get("/api/validate/{token}")
async def validate_user(token: str):
    res = supabase.table('users').select('email').eq('validation_token', token).execute()
    
    if len(res.data) == 0:
        return "Invalid validation token."
    
    email = res.data[0]['email']
    supabase.table('users').update({'is_validated': 1}).eq('validation_token', token).execute()
    
    # Notify User
    user_body = f"""
    <h2>Welcome to Gamepredict.ai!</h2>
    <p>Your account has been validated by our team.</p>
    <p>You can now log in and start using our premium prediction tools.</p>
    <a href="{BASE_URL}" style="display:inline-block; margin-top:15px; margin-bottom:15px; background:#6c5ce7; color:white; padding:10px 20px; text-decoration:none; border-radius:5px; font-weight:bold;">GO TO DASHBOARD</a>
    """
    await send_email(email, "Account Validated - Gamepredict.ai", user_body)
    
    return "User account validated successfully. A confirmation email has been sent to the user."

@app.post("/api/login")
async def login(req: LoginRequest):
    if not supabase:
        print("❌ CRITICAL: Supabase client is NOT initialized. Possible RLS or Private Key issue.")
        return JSONResponse(status_code=503, content={"message": "Database disconnected. Check Service Role Key."})
    
    email_normalized = req.email.lower().strip()
    res = supabase.table('users').select('id, password, is_validated, email').ilike('email', email_normalized).execute()
    if len(res.data) == 0:
        print(f"🔒 LOGIN FAILED: Email '{email_normalized}' NOT FOUND in database.")
        return JSONResponse(status_code=401, content={"message": "Invalid email or password"})
    
    user = res.data[0]
    u_id, hashed, is_val = user['id'], user['password'], user['is_validated']
    
    if not bcrypt.checkpw(req.password.encode('utf-8'), hashed.encode('utf-8')):
        print(f"🔒 LOGIN FAILED: Invalid password for email '{user.get('email')}'.")
        return JSONResponse(status_code=401, content={"message": "Invalid email or password"})
    
    if is_val == 0 or not is_val:
        return JSONResponse(status_code=403, content={"message": "Account pending validation by admin."})
    
    return {"message": "Login successful", "user_id": u_id}

@app.post("/api/lost_password")
async def lost_password(req: LostPasswordRequest):
    email_normalized = req.email.lower().strip()
    res = supabase.table('users').select('id').ilike('email', email_normalized).execute()
    if len(res.data) == 0:
        return {"message": "If this email is registered, a reset link has been sent."}
    
    reset_token = str(uuid.uuid4())
    supabase.table('users').update({'reset_token': reset_token}).eq('email', req.email).execute()
    
    reset_link = f"{BASE_URL}/?reset_token={reset_token}"
    body = f"""
    <h2>Password Reset Request</h2>
    <p>You requested to reset your password for Gamepredict.ai.</p>
    <p>Click the link below to set a new password:</p>
    <a href="{reset_link}" style="display:inline-block; margin-top:15px; margin-bottom:15px; background:#00d2ff; color:black; padding:10px 20px; text-decoration:none; border-radius:5px; font-weight:bold;">RESET PASSWORD</a>
    <p>If you didn't request this, you can safely ignore this email.</p>
    """
    await send_email(req.email, "Password Reset - Gamepredict.ai", body)
    
    return {"message": "If this email is registered, a reset link has been sent."}

@app.post("/api/reset_password")
async def reset_password(req: ResetPasswordRequest):
    res = supabase.table('users').select('email').eq('reset_token', req.token).execute()
    if len(res.data) == 0:
        return JSONResponse(status_code=400, content={"message": "Invalid or expired reset token."})
    
    hashed = bcrypt.hashpw(req.new_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    supabase.table('users').update({'password': hashed, 'reset_token': None}).eq('reset_token', req.token).execute()
    
    return {"message": "Password successfully updated. You can now log in."}

@app.post("/api/feedback")
async def feedback(req: FeedbackRequest):
    # Format the report email
    inputs = req.inputs
    results = req.results
    
    # Calculate total profit once (summing years + DLCs already done in results potentially)
    # But usually we display what comes from engine
    
    evolution_rows = ""
    for year, sales in zip(results.get('evolution_years', []), results.get('evolution_sales', [])):
        evolution_rows += f"<li><b>{year}:</b> {sales:,} copies</li>"

    html_body = f"""
    <div style="font-family: 'Outfit', sans-serif; color: #333; line-height: 1.6;">
        <h2 style="color: #00d2ff;">New Feedback / Prediction Report</h2>
        <p><b>User:</b> {req.user_email}</p>
        <p><b>Comment:</b> {req.comment}</p>
        
        <hr style="border: 0; border-top: 1px solid #eee; margin: 20px 0;">
        
        <h3 style="color: #444;">Form Inputs:</h3>
        <ul style="list-style: none; padding: 0;">
            <li><b>Game Name:</b> {inputs.get('game_name')}</li>
            <li><b>Genre:</b> {inputs.get('genre')}</li>
            <li><b>Budget:</b> ${int(inputs.get('budget', 0)):,}</li>
            <li><b>Wishlists:</b> {int(inputs.get('wishlists', 0)):,}</li>
            <li><b>Target Sentiment:</b> {inputs.get('sentiment_target')}%</li>
            <li><b>Buzz Score (IA):</b> {inputs.get('ia_buzz_score')}/10</li>
            <li><b>Fixed Price:</b> ${inputs.get('fixed_price') or 'AI Optimal'}</li>
            <li><b>Target Month:</b> {inputs.get('month')}</li>
            <li><b>Prev. Sales:</b> {inputs.get('prev_sales') or 'N/A'}</li>
            <li><b>Prev. Buzz:</b> {inputs.get('prev_buzz') or 'N/A'}</li>
            <li><b>DLCs:</b> {inputs.get('num_dlcs')} (@ ${inputs.get('dlc_price')})</li>
        </ul>
        
        <h3 style="color: #444;">AI Results:</h3>
        <ul style="list-style: none; padding: 0;">
            <li><b>Segment:</b> {results.get('label')}</li>
            <li><b>Optimal Price:</b> ${results.get('best_price', 0):.2f}</li>
            <li><b>Estimated Total Sales (5y):</b> {int(results.get('total_sales', 0)):,} copies</li>
            <li><b>Estimated Total Profit:</b> ${int(results.get('max_profit', 0)):,}</li>
        </ul>
        
        <h3 style="color: #444;">Sales Evolution:</h3>
        <ul>
            {evolution_rows}
        </ul>
    </div>
    """
    
    await send_email("mickurt@gmail.com", f"Feedback Prediction: {inputs.get('game_name')}", html_body)
    return {"message": "Feedback sent"}

class PredictionRequest(BaseModel):
    genre: str
    budget: float
    wishlists: int
    sentiment: int
    month: int
    langs: int
    gemini_key: Optional[str] = None
    similar_games_manual: Optional[str] = None

@app.get("/api/genres")
def get_genres():
    return engine.get_genres()

@app.post("/api/analyze_image")
async def analyze_image(
    file: UploadFile = File(...), 
    api_key: str = Form(None)
):
    final_key = api_key or GEMINI_DEFAULT_KEY
    if not final_key:
        return JSONResponse(status_code=400, content={"message": "Gemini API Key missing. Please provide it in the input field or set GOOGLE_API_KEY on the server."})
    
    print(f"Analyzing image: {file.filename} with Gemini...")
    content = await file.read()
    similars = engine.analyze_image_with_gemini(final_key, content, file.content_type)
    return {"similar_games": similars}

@app.post("/api/analyze_sentiment")
async def analyze_sentiment(
    game_name: str = Form(...),
    similar_games: str = Form(None),
    api_key: str = Form(None)
):
    final_key = api_key or GEMINI_DEFAULT_KEY
    if not final_key:
        # We can also silent fail or use a default score, but let's notify
        return JSONResponse(status_code=400, content={"message": "Gemini API Key missing for buzz analysis."})

    print(f"Analyzing sentiment for: {game_name}")
    result = engine.analyze_sentiment_buzz(final_key, game_name, similar_games or "")
    
    # NEW: Enrich with local DB data for more accuracy
    result = engine.enrich_predecessor_data(result)
    
    return result


@app.post("/api/predict")
async def predict(
    genre: str = Form(...),
    budget: float = Form(0),
    wishlists: Optional[int] = Form(None),
    sentiment: Optional[int] = Form(None),
    month: int = Form(10),
    langs: int = Form(5),
    similar_games: str = Form(None),
    game_name: str = Form(None),
    sentiment_ia_score: float = Form(None),
    fixed_price: float = Form(None),
    previous_sales: int = Form(None),
    previous_sentiment: int = Form(None),
    previous_buzz: int = Form(None),
    num_dlcs: int = Form(0),
    dlc_price: float = Form(0.0),
    user_id: str = Form(None)
):
    
    sim_list = []
    if similar_games:
        sim_list = [s.strip() for s in similar_games.split(',') if s.strip()]
    
    try:
        result = engine.predict_optimization(
            genre_name=genre,
            budget=budget,
            wishlists=wishlists,
            reviews_target=0, # unused
            sentiment_target=sentiment,
            month=month,
            langs=langs,
            similar_games=sim_list,
            game_name=game_name,
            sentiment_ia_score=sentiment_ia_score,
            fixed_price=fixed_price,
            previous_sales=previous_sales,
            previous_sentiment=previous_sentiment,
            previous_buzz=previous_buzz,
            num_dlcs=num_dlcs,
            dlc_price=dlc_price
        )
        
        # Save prediction to database
        try:
            supabase.table('predictions').insert({
                'user_id': user_id or "Guest",
                'game_name': game_name or "",
                'genre': genre,
                'budget': float(budget),
                'wishlists': int(wishlists),
                'sentiment_target': int(sentiment),
                'month': int(month),
                'langs': int(langs),
                'similar_games': similar_games or "",
                'fixed_price': float(fixed_price) if fixed_price is not None else None,
                'previous_sales': int(previous_sales) if previous_sales is not None else None,
                'previous_sentiment': int(previous_sentiment) if previous_sentiment is not None else None,
                'previous_buzz': int(previous_buzz) if previous_buzz is not None else None,
                'num_dlcs': int(num_dlcs),
                'dlc_price': float(dlc_price),
                'best_price': float(result.get('best_price', 0)),
                'max_profit': float(result.get('max_profit', 0)),
                'est_total_sales': int(result.get('est_total_sales', 0)),
                'segment_label': result.get('segment_label', 'Unknown')
            }).execute()
        except Exception as e:
            print(f"Failed to log prediction to Supabase DB: {e}")
            
        return result
    except Exception as e:
        import traceback
        traceback.print_exc()
        # Return 500 so frontend catch block shows the error
        from fastapi.responses import JSONResponse
        return JSONResponse(status_code=500, content={"message": str(e)})

# Mount Static Files (Frontend)
# We mount this LAST to avoid conflicts with API routes
static_dir = os.path.join(os.path.dirname(__file__), "static")
if not os.path.exists(static_dir):
    os.makedirs(static_dir)

app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 7860))
    uvicorn.run(app, host="0.0.0.0", port=port)

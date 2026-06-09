##  Quick Overview

This backend provides:
- **Scholarship Filtering**: AI-powered scholarship matching using OpenAI GPT-4o
- **Vector Search**: Fast scholarship discovery using Pinecone embeddings
- **Multi-language Support**: English & Swedish translations
- **Payment Integration**: Stripe payment processing with coupon support
- **Applicant Management**: Track applications and email verification
- **Admin Panel**: Manage scholarships, coupons, and settings

---

##  Getting Started (5 Minutes)

### 1. **Prerequisites**
Make sure you have:
- Python 3.10 or higher
- pip (Python package manager)
- Git
- A Windows/Mac/Linux terminal

### 2. **Clone & Setup Project**

```bash
# Navigate to your projects folder path
cd "C:\Users\Salman Farsi\OneDrive\Desktop\python"

# Enter the project folder 
cd stepo_backend(foysal)

# Create a virtual environment (if not already done)
python -m venv venv

# Activate the virtual environment
# On Windows:
venv\Scripts\activate

# On Mac/Linux:
source venv/bin/activate
```

### 3. **Install Dependencies**

```bash
# Install required packages also check the file name is requirements.txt or not
pip install -r stepo_backend/requirements.txt
```

### 4. **Create Environment File**

Create a `.env` file in the `stepo_backend/` folder with the following variables:

```env
# OpenAI API (for scholarship filtering)
OPENAI_API_KEY=your_openai_key_here

# Pinecone (for vector search)
PINECONE_API_KEY=your_pinecone_key_here

# Stripe (for payments)
STRIPE_SECRET_KEY=your_stripe_secret_key_here
STRIPE_PUBLIC_KEY=your_stripe_public_key_here

# Email Configuration (for OTP & notifications)
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=your_email@gmail.com
EMAIL_HOST_PASSWORD=your_app_password_here

# Django Debug (development only)
DEBUG=True
SECRET_KEY=your_django_secret_key_here
```

### 5. **Run Database Migrations**

```bash
cd stepo_backend

# Apply all migrations
python manage.py migrate

# Create a superuser (admin account)
python manage.py createsuperuser
# Follow the prompts to enter username, email, and password
```

### 6. **Start the Server**

```bash
# Run development server
python manage.py runserver 8090

# Server will be available at:
# http://localhost:8000
# Admin panel: http://localhost:8000/admin
```
```bash
# Run development server
# Server will be available at:
# http://localhost:8000
# Admin panel: http://localhost:8000/admin
```

---

##  Environment Variables Explained

| Variable | What It Does | Where to Get It |
|----------|-------------|-----------------|
| `OPENAI_API_KEY` | Powers the AI scholarship filtering | [OpenAI Platform](https://platform.openai.com/account/api-keys) |
| `PINECONE_API_KEY` | Enables fast vector search for scholarships | [Pinecone Console](https://app.pinecone.io) |
| `STRIPE_SECRET_KEY` | Secret key for payment processing | [Stripe Dashboard](https://dashboard.stripe.com/apikeys) |
| `STRIPE_PUBLIC_KEY` | Public key for frontend payment forms | [Stripe Dashboard](https://dashboard.stripe.com/apikeys) |
| `EMAIL_HOST_USER` | Your Gmail address (for sending verification emails) | Your Gmail account |
| `EMAIL_HOST_PASSWORD` | Gmail app-specific password | [Gmail Security Settings](https://myaccount.google.com/apppasswords) |

### Getting Gmail App Password (Email)

1. Go to [https://myaccount.google.com/security](https://myaccount.google.com/security)
2. Enable **2-Step Verification** (if not already enabled)
3. Go back to Security → **App passwords**
4. Select "Mail" and "Windows Computer"
5. Copy the generated 16-character password
6. Use this as `EMAIL_HOST_PASSWORD` in your `.env` file

---

##  Loading Scholarship Data into Pinecone

### Method 1: Upload via Admin Panel (Easiest)

1. **Start the server**:
   ```bash
   python manage.py runserver
   ```

2. **Go to Admin Panel**:
   - Visit: `http://localhost:8000/admin`
   - Login with your superuser credentials

3. **Upload Scholarship Database**:
   - Click on **Site Config**
   - Scroll to **"Scholarships DB File"**
   - Click **"Choose File"**
   - Select your `new_scholarships_db.xlsx` file
   - Make sure **"Pinecone Updated"** is unchecked
   - Click **Save**

4. **Wait for Upload**:
   - The system will automatically:
     - Read the Excel file
     - Create embeddings for each scholarship
     - Upload to Pinecone
     - Update the database
   - Check the Django logs to see progress

### Method 2: Manual Upload (Advanced)

If you prefer command-line:

```bash
cd stepo_backend

# Run the embedding script
python embed1.py  # This uploads the scholarships to Pinecone

# Or use the management command:
# python manage.py load_scholarships_to_pinecone
```

### Verifying the Upload

1. **Check Pinecone Dashboard**:
   - Go to [https://app.pinecone.io](https://app.pinecone.io)
   - You should see vectors in your index (e.g., "scholarships-index-latest")
   - Verify the vector count matches your Excel file

2. **Check Admin Panel**:
   - Go to **Site Config** → **Available Dataset Indices**
   - Confirm the index is listed

---

##  Testing the API

### Test Scholarship Search

```bash
# Open a new terminal and run:

# Get available scholarships
curl http://localhost:8000/api/scholarships/

# Or use Python:
python
>>> import requests
>>> response = requests.get('http://localhost:8000/api/scholarships/')
>>> print(response.json())
```

### Test Application Submission

```bash
curl -X POST http://localhost:8000/api/submit-application/ \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "study_level": "undergraduate",
    "user_purpose": "I want to study engineering",
    "gender": "male",
    "municipality": "Stockholm"
  }'
```

---

## Using ngrok to Test Webhooks Locally


### Installation

#### Windows:

1. **Download ngrok** from [https://ngrok.com/download](https://ngrok.com/download)
2. **Extract the zip file** to a folder (e.g., `C:\ngrok`)
3. **Verify installation**:
   ```bash
   # Add ngrok to PATH (optional but recommended)
   # Open PowerShell as Admin and run:
   setx PATH "%PATH%;C:\ngrok"
   
   # Test it works
   ngrok --version
   ```

#### Mac:

```bash
# Install via Homebrew
brew install ngrok

# Or download from https://ngrok.com/download
```

#### Linux:

```bash
# Download and extract
wget https://bin.equinox.io/c/bNyj1mQVY4c/ngrok-v3-stable-linux-amd64.zip
unzip ngrok-v3-stable-linux-amd64.zip

# Move to PATH
sudo mv ngrok /usr/local/bin/
```

### Setup ngrok

1. **Create a free account** at [https://ngrok.com](https://ngrok.com)

2. **Get your auth token**:
   - Log in to your ngrok account
   - Go to **Auth** → Copy your token
   - In terminal, run:
   ```bash
   ngrok config add-authtoken YOUR_TOKEN_HERE
   ```

3. **Verify it's configured**:
   ```bash
   ngrok --help
   ```

### Starting ngrok

#### Step 1: Start Django Server (in terminal 1)

```bash
cd stepo_backend
python manage.py runserver
# Server running on http://localhost:8000
```

#### Step 2: Start ngrok (in terminal 2)

```bash
# Create a public URL for your local server
ngrok http 8090


```bash


##  Project Structure

```
stepo_backend/
├── app/
│   ├── models.py              # Database models (Coupon, Scholarship, etc.)
│   ├── views.py               # API endpoints
│   ├── serializers.py         # Data serializers
│   ├── urls.py                # URL routing
│   ├── admin.py               # Admin panel configuration
│   ├── migrations/            # Database migrations
│   └── tests.py               # Test cases
│
├── stipo54.py                 # Core scholarship filtering logic
├── stipo47.py                 # Alternative matching algorithm
├── embed1.py                  # Pinecone embedding & upload
├── manage.py                  # Django management commands
├── requirements.txt           # Python dependencies
├── db.sqlite3                 # SQLite database (auto-created)
└── .env                       # Environment variables (create this)
```

---

## Troubleshooting

### "ModuleNotFoundError: No module named 'pinecone'"

**Solution**: Install requirements again
```bash
pip install -r stepo_backend/requirements.txt
pip install pinecone-client openai
```

### "OPENAI_API_KEY not found"

**Solution**: 
- Check that `.env` file exists in `stepo_backend/` folder
- Verify the key is correct: `OPENAI_API_KEY=sk-...`
- Restart the server after editing `.env`

### "Pinecone index error: Name must consist of lower case alphanumeric characters or '-'"

**Solution**: 
- Index names in Pinecone must be lowercase with hyphens only (no underscores)
- Go to Admin Panel → Site Config
- Set **Active Dataset Index Name** to lowercase with hyphens: `scholarships-index-latest`
- The system automatically converts underscores to hyphens

### "No scholarships found in Pinecone"

**Solution**:
1. Check Pinecone dashboard to verify vectors exist
2. Verify the index name matches in Admin Panel → Site Config
3. Try re-uploading the scholarship data:
   - Go to Admin Panel → Site Config
   - Uncheck **Pinecone Updated**
   - Re-upload the Excel file
   - Check Django logs for errors

### "Email verification not working"

**Solution**: 
- Verify `EMAIL_HOST_USER` and `EMAIL_HOST_PASSWORD` in `.env`
- For Gmail, use an [app-specific password](https://myaccount.google.com/apppasswords)
- Check that 2-Step Verification is enabled on Gmail
- Try sending a test email in Django shell:
  ```bash
  python manage.py shell
  >>> from django.core.mail import send_mail
  >>> send_mail('Test', 'Message', 'from@gmail.com', ['to@example.com'])
  ```

### "Stripe payment not working"

**Solution**:
- Verify `STRIPE_SECRET_KEY` and `STRIPE_PUBLIC_KEY` in `.env`
- Use test keys from Stripe dashboard for development
- Check Stripe webhook configuration in your Stripe dashboard

### Server won't start / Database locked

**Solution**:
```bash
# Delete the old database and start fresh
rm db.sqlite3

# Re-run migrations
python manage.py migrate

# Create new admin user
python manage.py createsuperuser

# Start server
python manage.py runserver
```

---

## Common Tasks

### Add a New Coupon

1. Go to Admin Panel: `http://localhost:8000/admin`
2. Click **Coupons** → **Add Coupon**
3. Fill in:
   - **Discount**: 20 (for 20% off)
   - **Max Uses**: 100 (or leave blank for unlimited)
   - **Active**: Check to enable
4. Click **Save** (code auto-generates)

### View Coupon Usage

1. Go to Admin Panel → **Coupons**
2. See the **Usage** column showing: `30.0% (15/50)` means 15 used out of 50 max
3. Click on a coupon to see:
   - **Times Used**
   - **Last Used**
   - **Status** (Active/Disabled/Limit Reached)

### Disable a Coupon

1. Admin Panel → **Coupons**
2. Click the coupon code
3. Uncheck **Active**
4. Click **Save**

### Change Scholarship Filtering Settings

1. Admin Panel → **Site Config**
2. Edit **LLM Filter System Prompt** for matching logic
3. Edit **LLM Reranker System Prompt** for ranking
4. Check/uncheck **Use Default Prompts** to use hardcoded defaults
5. Click **Save**

---

## Running Tests

```bash
cd stepo_backend

# Run all tests
python manage.py test

# Run tests for a specific app
python manage.py test app

# Run with verbose output
python manage.py test -v 2
```

---

## API Endpoints Summary

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/scholarships/` | GET | List all scholarships |
| `/api/submit-application/` | POST | Submit a new application |
| `/api/verify-email/` | POST | Verify email with OTP |
| `/api/generate-payment-link/` | POST | Generate Stripe payment link |
| `/api/coupons/validate/` | POST | Validate coupon code |

---

## Support & Questions

If you encounter issues:
1. Check the **Troubleshooting** section above
2. Review Django error logs in your terminal
3. Check Pinecone dashboard for vector status
4. Verify all environment variables are set correctly

---

##Checklist Before Going Live

- [ ] All environment variables in `.env` are set
- [ ] Database migrations completed (`python manage.py migrate`)
- [ ] Scholarship data uploaded to Pinecone
- [ ] Admin account created (`python manage.py createsuperuser`)
- [ ] Email configuration tested (OTP sending works)
- [ ] Stripe keys verified (test keys for dev, live keys for production)
- [ ] Pinecone index verified and populated
- [ ] Server runs without errors: `python manage.py runserver`

---

**Version**: 1.0  
**Last Updated**: June 2026  
**Framework**: Django 4.2+ | Python 3.10+

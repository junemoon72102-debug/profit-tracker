# ProfitIQ — E-commerce Profit Intelligence

A clean, production-style SaaS dashboard for e-commerce profit tracking.

## Setup (5 minutes)

### 1. Requirements
- Python 3.8+
- pip

### 2. Install dependencies
```bash
pip install -r requirements.txt
```

### 3. Run
```bash
python app.py
```

Open **http://localhost:5000** in your browser.

### 4. First steps
1. Create an account on the login screen
2. Sign in
3. Click **"Load sample data"** on the dashboard to populate 5 example products
4. Explore the Products and Reports pages

---

## Pages

| Page | URL | Description |
|------|-----|-------------|
| Login | `/login` | Sign in / create account |
| Dashboard | `/dashboard` | KPI cards, charts, smart suggestions |
| Products | `/products` | Add/edit/delete products + what-if analysis |
| Reports | `/reports` | Full detail table + CSV export |

## Project Structure

```
ecommerce-profit-app/
├── app.py                  # Flask backend, all routes + API
├── requirements.txt
├── database/               # SQLite DB auto-created here
├── static/
│   └── css/
│       ├── style.css       # Main app styles
│       └── login.css       # Login page styles
└── templates/
    ├── login.html
    ├── sidebar.html        # Shared nav component
    ├── dashboard.html
    ├── products.html
    └── reports.html
```

## Profit Formula

```
Return Loss  = Selling Price × (Return Rate / 100)
Total Costs  = Cost Price + Ad Spend + Platform Fees + Delivery Cost + Return Loss
Profit       = Selling Price − Total Costs
Margin (%)   = (Profit / Selling Price) × 100
```

## Smart Suggestions Logic

| Condition | Suggestion |
|-----------|-----------|
| Profit < 0 | Stop selling this product |
| Margin < 15% | Reduce ad spend or optimize costs |
| Margin ≥ 15% | Scale this product |

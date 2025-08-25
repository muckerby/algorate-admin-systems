# Algorate Meetings Import Service

A production-ready Flask service for importing horse racing meeting data from the Punting Form API into Supabase database, with a comprehensive admin dashboard for management and monitoring.

## Features

### 🔄 Data Import
- **Automated daily imports** from Punting Form API
- **Manual import triggers** via admin dashboard
- **Upsert functionality** (insert new, update existing meetings)
- **Comprehensive error handling** and retry logic

### 📊 Admin Dashboard
- **Real-time status monitoring** with auto-refresh
- **Import history logs** with color-coded status
- **Manual import controls** with date picker (DD/MM/YYYY format)
- **API connectivity testing** 
- **Responsive design** for desktop and mobile

### 🗄️ Database Integration
- **Supabase PostgreSQL** backend
- **Row Level Security (RLS)** enabled
- **Import logging** with detailed statistics
- **Australian date/time formatting** (DD/MM/YYYY, AEST)

## Architecture

- **Backend:** Flask with SQLAlchemy ORM
- **Frontend:** Vanilla JavaScript with modern UI
- **Database:** Supabase PostgreSQL
- **API:** Punting Form API v2 integration
- **Deployment:** Railway (Singapore region)
- **Scheduling:** APScheduler for automated imports

## Environment Variables

```bash
# Punting Form API
PUNTING_FORM_API_KEY=your_api_key_here

# Supabase Database
SUPABASE_URL=your_supabase_url_here
SUPABASE_SERVICE_ROLE_KEY=your_service_role_key_here

# Flask Configuration
FLASK_ENV=production
SECRET_KEY=your_secret_key_here
```

## API Endpoints

### Import Management
- `POST /api/import/meetings` - Trigger manual import
- `GET /api/import/meetings/status` - Get last import status
- `GET /api/import/meetings/logs` - Get import history
- `GET /api/import/meetings/test` - Test API connectivity

## Local Development

1. **Clone repository**
```bash
git clone <repository-url>
cd algorate-meetings-import
```

2. **Set up virtual environment**
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies**
```bash
pip install -r requirements.txt
```

4. **Configure environment variables**
```bash
cp .env.example .env
# Edit .env with your actual credentials
```

5. **Run development server**
```bash
python src/main.py
```

6. **Access admin dashboard**
```
http://localhost:5000
```

## Deployment

### Railway Deployment

1. **Connect to Railway**
   - Create new Railway project
   - Connect GitHub repository
   - Select Singapore region (asia-southeast1)

2. **Configure environment variables**
   - Add all required environment variables in Railway dashboard
   - Ensure service role key has proper Supabase permissions

3. **Deploy**
   - Railway will automatically build and deploy
   - Access via generated Railway domain

### Database Setup

1. **Supabase Configuration**
   - Ensure `meetings` table exists with proper schema
   - Enable Row Level Security (RLS)
   - Create service role policy for full access

2. **Import Logs Table**
   - Table will be created automatically on first run
   - Stores comprehensive import history and statistics

## Monitoring

- **Admin Dashboard:** Real-time status and logs
- **Railway Logs:** Application and deployment logs
- **Supabase Dashboard:** Database monitoring and queries

## Security

- **RLS Policies:** Database-level security
- **Service Role Authentication:** Secure API access
- **CORS Enabled:** Cross-origin request support
- **Environment Variables:** Secure credential storage

## Support

For issues or questions regarding the Algorate Meetings Import Service, please refer to the import logs in the admin dashboard or check Railway deployment logs.

---

**Algorate** - Advanced Horse Racing Analytics Platform


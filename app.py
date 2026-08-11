from flask import Flask, render_template, request, jsonify, send_file, session, redirect, url_for
from functools import wraps
import os
import json
import sqlite3
import base64
from datetime import datetime, timedelta
from dotenv import load_dotenv
from db_init import init_db, DB_PATH
from pdf_gen import generate_invoice_pdf
import sib_api_v3_sdk
from sib_api_v3_sdk.rest import ApiException

load_dotenv()

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'heaven-in-a-bite-secret-key-change-in-production')
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=2) # Longer sessions for easier iPad usage

# Run DB Initialization
init_db()

USERNAME    = os.environ.get('APP_USERNAME', 'admin')
PASSWORD    = os.environ.get('APP_PASSWORD', 'heaven2026')
BREVO_KEY   = os.environ.get('BREVO_API_KEY', '')
SENDER_EMAIL = os.environ.get('SENDER_EMAIL', 'accounts@heaveninabite.co.za')

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'logged_in' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# Health Check Route for Docker Container
@app.route('/health')
def health():
    try:
        conn = get_db_connection()
        conn.execute('SELECT 1')
        conn.close()
        return jsonify({"status": "healthy", "database": "connected"}), 200
    except Exception as e:
        return jsonify({"status": "unhealthy", "error": str(e)}), 500

# Root Index Redirect
@app.route('/')
def index():
    if 'logged_in' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

# Login Route
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        if username == USERNAME and password == PASSWORD:
            session.permanent = True
            session['logged_in'] = True
            session['username'] = username
            return redirect(url_for('dashboard'))
        return render_template('login.html', error='Invalid credentials')
    return render_template('login.html')

# Logout Route
@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# Dashboard View
@app.route('/dashboard')
@login_required
def dashboard():
    conn = get_db_connection()
    status_filter = request.args.get('status', 'all')
    search_query = request.args.get('search', '').strip()
    
    query = 'SELECT * FROM invoices WHERE 1=1'
    params = []
    
    if status_filter in ['Paid', 'Unpaid']:
        query += ' AND status = ?'
        params.append(status_filter)
        
    if search_query:
        query += ' AND (client_name LIKE ? OR invoice_number LIKE ?)'
        params.append(f'%{search_query}%')
        params.append(f'%{search_query}%')
        
    query += ' ORDER BY id DESC'
    invoices = conn.execute(query, params).fetchall()
    
    # Calculate stats
    total_invoiced = conn.execute('SELECT SUM(total_amount) FROM invoices').fetchone()[0] or 0.0
    unpaid_total = conn.execute('SELECT SUM(total_amount) FROM invoices WHERE status = "Unpaid"').fetchone()[0] or 0.0
    paid_total = conn.execute('SELECT SUM(total_amount) FROM invoices WHERE status = "Paid"').fetchone()[0] or 0.0
    
    conn.close()
    return render_template('dashboard.html', 
                           invoices=invoices, 
                           status_filter=status_filter,
                           search_query=search_query,
                           total_invoiced=total_invoiced,
                           unpaid_total=unpaid_total,
                           paid_total=paid_total)

# Create / Add Invoice
@app.route('/invoice/new', methods=['GET', 'POST'])
@login_required
def create_invoice():
    if request.method == 'POST':
        client_option = request.form.get('client_option')
        if client_option == 'Other':
            client_name = request.form.get('client_name_other', '').strip()
        else:
            client_name = client_option
            
        date_str = request.form.get('date') or datetime.now().strftime('%Y-%m-%d')
        status = request.form.get('status', 'Unpaid')
        
        descs  = request.form.getlist('item_desc[]')
        qtys   = request.form.getlist('item_qty[]')
        prices = request.form.getlist('item_price[]')

        items = []
        total_amount = 0.0
        for desc, qty, price in zip(descs, qtys, prices):
            q = int(qty or 1)
            p = float(price or 0.0)
            items.append({"description": desc.strip(), "qty": q, "price": p})
            total_amount += q * p
                
        # Generate clean invoice number (e.g. INV-YEAR-00X)
        conn = get_db_connection()
        year = datetime.now().year
        last_invoice = conn.execute("SELECT invoice_number FROM invoices ORDER BY id DESC LIMIT 1").fetchone()
        
        next_id = 55
        if last_invoice:
            try:
                # Extract sequence digits from end of number
                parts = last_invoice['invoice_number'].split('-')
                if len(parts) == 3:
                    next_id = int(parts[2]) + 1
            except Exception:
                pass
                
        invoice_number = f"INV-{year}-{next_id:04d}"
        
        conn.execute('''
            INSERT INTO invoices (invoice_number, date, client_name, client_email, client_phone, items, total_amount, status, special_notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            invoice_number,
            date_str,
            client_name,
            '', # empty email
            '', # empty phone
            json.dumps(items),
            total_amount,
            status,
            ''  # empty special notes
        ))
        conn.commit()
        conn.close()
        
        return redirect(url_for('dashboard'))
        
    # GET: Pre-generate a date string for the input
    today_str = datetime.now().strftime('%Y-%m-%d')
    
    # Calculate upcoming invoice number
    conn = get_db_connection()
    year = datetime.now().year
    last_invoice = conn.execute("SELECT invoice_number FROM invoices ORDER BY id DESC LIMIT 1").fetchone()
    next_id = 55
    if last_invoice:
        try:
            parts = last_invoice['invoice_number'].split('-')
            if len(parts) == 3:
                next_id = int(parts[2]) + 1
        except Exception:
            pass
    conn.close()
    upcoming_invoice_number = f"INV-{year}-{next_id:04d}"
    
    return render_template('invoice_form.html', today_str=today_str, invoice=None, items_list=None, upcoming_invoice_number=upcoming_invoice_number)

# Edit / Update Invoice Status or details
@app.route('/invoice/<int:invoice_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_invoice(invoice_id):
    conn = get_db_connection()
    invoice = conn.execute('SELECT * FROM invoices WHERE id = ?', (invoice_id,)).fetchone()
    
    if not invoice:
        conn.close()
        return "Invoice not found", 404
        
    if request.method == 'POST':
        client_option = request.form.get('client_option')
        if client_option == 'Other':
            client_name = request.form.get('client_name_other', '').strip()
        else:
            client_name = client_option
            
        date_str = request.form.get('date')
        status = request.form.get('status', 'Unpaid')
        
        descs  = request.form.getlist('item_desc[]')
        qtys   = request.form.getlist('item_qty[]')
        prices = request.form.getlist('item_price[]')

        items = []
        total_amount = 0.0
        for desc, qty, price in zip(descs, qtys, prices):
            q = int(qty or 1)
            p = float(price or 0.0)
            items.append({"description": desc.strip(), "qty": q, "price": p})
            total_amount += q * p
                
        conn.execute('''
            UPDATE invoices
            SET client_name = ?, client_email = ?, client_phone = ?, date = ?, items = ?, total_amount = ?, status = ?, special_notes = ?
            WHERE id = ?
        ''', (
            client_name,
            '', # empty email
            '', # empty phone
            date_str,
            json.dumps(items),
            total_amount,
            status,
            '', # empty special notes
            invoice_id
        ))
        conn.commit()
        conn.close()
        
        # If there is a generated PDF file, remove it so it recreates on next preview
        pdf_filename = f"invoice_{invoice['invoice_number']}.pdf"
        pdf_path = os.path.join('data/exports', pdf_filename)
        if os.path.exists(pdf_path):
            try:
                os.remove(pdf_path)
            except Exception:
                pass
                
        return redirect(url_for('dashboard'))
        
    # Parse items JSON for HTML layout pre-fill
    items_list = json.loads(invoice['items'])
    upcoming_invoice_number = invoice['invoice_number']
    conn.close()
    return render_template('invoice_form.html', invoice=invoice, items_list=items_list, today_str=invoice['date'], upcoming_invoice_number=upcoming_invoice_number)

# Delete Invoice
@app.route('/invoice/<int:invoice_id>/delete', methods=['POST'])
@login_required
def delete_invoice(invoice_id):
    conn = get_db_connection()
    invoice = conn.execute('SELECT invoice_number FROM invoices WHERE id = ?', (invoice_id,)).fetchone()
    if invoice:
        # Clean up files
        pdf_filename = f"invoice_{invoice['invoice_number']}.pdf"
        pdf_path = os.path.join('data/exports', pdf_filename)
        if os.path.exists(pdf_path):
            try:
                os.remove(pdf_path)
            except Exception:
                pass
        conn.execute('DELETE FROM invoices WHERE id = ?', (invoice_id,))
        conn.commit()
    conn.close()
    return redirect(url_for('dashboard'))

# Send Email via Brevo
@app.route('/invoice/<int:invoice_id>/email', methods=['POST'])
@login_required
def send_email_trigger(invoice_id):
    conn = get_db_connection()
    invoice_row = conn.execute('SELECT * FROM invoices WHERE id = ?', (invoice_id,)).fetchone()
    conn.close()

    if not invoice_row:
        return "Invoice not found", 404

    invoice = dict(invoice_row)

    # Generate PDF if it doesn't exist
    pdf_filename = f"invoice_{invoice['invoice_number']}.pdf"
    pdf_path = os.path.join('data/exports', pdf_filename)
    if not os.path.exists(pdf_path):
        os.makedirs('data/exports', exist_ok=True)
        generate_invoice_pdf(invoice, pdf_path)

    # Read & base64-encode the PDF for attachment
    with open(pdf_path, 'rb') as f:
        pdf_b64 = base64.b64encode(f.read()).decode('utf-8')

    # Build email body
    html_body = f"""
    <div style="font-family:Arial,sans-serif;max-width:600px;margin:0 auto;color:#202020;">
        <h2 style="color:#c5a880;border-bottom:1px solid #e0d8cb;padding-bottom:10px;">
            Heaven in a Bite — Invoice {invoice['invoice_number']}
        </h2>
        <p>Dear <strong>{invoice['client_name']}</strong>,</p>
        <p>Please find your invoice attached for <strong>R {float(invoice['total_amount']):,.2f}</strong>.</p>
        <table style="width:100%;border-collapse:collapse;margin:20px 0;">
            <tr style="background:#f5eedf;">
                <td style="padding:10px;font-weight:bold;">Invoice No</td>
                <td style="padding:10px;">{invoice['invoice_number']}</td>
            </tr>
            <tr>
                <td style="padding:10px;font-weight:bold;">Date Issued</td>
                <td style="padding:10px;">{invoice['date']}</td>
            </tr>
            <tr style="background:#f5eedf;">
                <td style="padding:10px;font-weight:bold;">Amount Due</td>
                <td style="padding:10px;color:#c62828;font-weight:bold;">R {float(invoice['total_amount']):,.2f}</td>
            </tr>
            <tr>
                <td style="padding:10px;font-weight:bold;">Status</td>
                <td style="padding:10px;">{invoice['status']}</td>
            </tr>
        </table>
        <div style="background:#f5eedf;padding:16px;border-radius:6px;margin:20px 0;">
            <p style="margin:0 0 6px;font-weight:bold;">Banking Details</p>
            <p style="margin:2px 0;">Bank: FNB (First National Bank)</p>
            <p style="margin:2px 0;">Account Name: KK Constantinou</p>
            <p style="margin:2px 0;">Account Number: 63182442920</p>
            <p style="margin:2px 0;">Branch Code: 253442</p>
            <p style="margin:2px 0;">Reference: <strong>{invoice['invoice_number']}</strong></p>
        </div>
        <p>Thank you for choosing Heaven in a Bite!</p>
        <p style="color:#c5a880;font-size:12px;">Koulla Constantinou &bull; accounts@heaveninabite.co.za &bull; +27 84 202 0100</p>
    </div>
    """

    # Configure Brevo API
    configuration = sib_api_v3_sdk.Configuration()
    configuration.api_key['api-key'] = BREVO_KEY
    api_instance = sib_api_v3_sdk.TransactionalEmailsApi(sib_api_v3_sdk.ApiClient(configuration))

    recipient_email = request.form.get('recipient_email', '').strip()
    if not recipient_email:
        return "No recipient email provided", 400

    send_smtp_email = sib_api_v3_sdk.SendSmtpEmail(
        sender={"name": "Heaven in a Bite", "email": SENDER_EMAIL},
        to=[{"email": recipient_email, "name": invoice['client_name']}],
        reply_to={"email": SENDER_EMAIL, "name": "Heaven in a Bite"},
        subject=f"Invoice {invoice['invoice_number']} — Heaven in a Bite",
        html_content=html_body,
        attachment=[{
            "content": pdf_b64,
            "name": pdf_filename
        }]
    )

    try:
        api_instance.send_transac_email(send_smtp_email)
        print(f"BREVO: Sent {invoice['invoice_number']} to {SENDER_EMAIL}")
        return redirect(url_for('dashboard', email_sent=invoice['invoice_number']))
    except ApiException as e:
        print(f"BREVO ERROR: {e}")
        return redirect(url_for('dashboard', email_sent=f"FAILED-{invoice['invoice_number']}"))

# View / Preview HTML layout or Download PDF
@app.route('/invoice/<int:invoice_id>/pdf')
@login_required
def download_pdf(invoice_id):
    conn = get_db_connection()
    invoice_row = conn.execute('SELECT * FROM invoices WHERE id = ?', (invoice_id,)).fetchone()
    conn.close()
    
    if not invoice_row:
        return "Invoice not found", 404
        
    invoice = dict(invoice_row)
    pdf_filename = f"invoice_{invoice['invoice_number']}.pdf"
    pdf_path = os.path.join('data/exports', pdf_filename)
    
    # Generate on the fly if file doesn't exist
    if not os.path.exists(pdf_path):
        os.makedirs('data/exports', exist_ok=True)
        generate_invoice_pdf(invoice, pdf_path)
        
    return send_file(pdf_path, as_attachment=False, download_name=pdf_filename)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5004, debug=True)

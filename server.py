from http.server import BaseHTTPRequestHandler, HTTPServer
import psycopg2
import urllib.parse as urlparse
import os
import http.cookies
from jinja2 import Template

# Настройки базы данных
DB_NAME = 'lab'
DB_USER = 'postgres'
DB_PASSWORD = 'Zx123987'
DB_HOST = 'localhost'
DB_PORT = '5432'

# Получаем абсолютный путь к директории проекта
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

class SimpleHTTPRequestHandler(BaseHTTPRequestHandler):

    def do_GET(self):
        try:
            if self.path == '/':
                self.check_auth_and_serve_template('index.html')
            elif self.path == '/signup':
                self.serve_template('signup.html')
                
            elif self.path == '/user_profile':
                self.check_patient('user_profile.html')

            elif self.path == '/login':
                self.serve_template('login.html')

            elif self.path.startswith('/static/'):
                self.serve_static(self.path[1:])
        except Exception as e:
            self.send_error(500, f'Internal Server Error: {str(e)}')

    def do_POST(self):
        try:
            if self.path == '/signup':
                self.handle_signup()

            elif self.path == '/login':
                self.handle_login()
        except Exception as e:
            self.send_error(500, f'Internal Server Error: {str(e)}')

    def handle_signup(self):
        length = int(self.headers.get('Content-Length'))
        post_data = self.rfile.read(length)
        params = urlparse.parse_qs(post_data.decode('utf-8'))
        username = params['username'][0]
        password = params['password'][0]
        full_name = params['full_name'][0]
        date_of_birth = params['date_of_birth'][0]
        phone = params['phone'][0]

        conn = psycopg2.connect(
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD,
            host=DB_HOST,
            port=DB_PORT
        )
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO patients (username, password, full_name, date_of_birth, phone) VALUES (%s, %s, %s, %s, %s)",
            (username, password, full_name, date_of_birth, phone)
        )
        conn.commit()
        cursor.close()
        conn.close()

        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.set_cookie('username', username)
        self.end_headers()
        self.wfile.write(b'<h1>Sign Up Successful</h1><a href="/">Go to Home</a>')

    def handle_login(self):
        length = int(self.headers.get('Content-Length'))
        post_data = self.rfile.read(length)
        params = urlparse.parse_qs(post_data.decode('utf-8'))
        username = params['username'][0]
        password = params['password'][0]

        conn = psycopg2.connect(
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD,
            host=DB_HOST,
            port=DB_PORT
        )
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM patients WHERE username = %s AND password = %s", (username, password))
        user = cursor.fetchone()
        cursor.close()
        conn.close()

        if user:
            print("YES")
            self.send_response(302)  # Используем код 302 для перенаправления
            self.send_header('Location', '/user_profile')  # Перенаправляем на user_profile.html
            self.set_cookie('username', username)
            self.end_headers()
        else:
            self.send_response(401)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            self.wfile.write(b'<h1>Login Failed</h1><a href="/login">Try Again</a>')

    def serve_template(self, template_name, context=None):
        context = context or {}
        template_path = os.path.join(BASE_DIR, 'templates', template_name)
        try:
            with open(template_path, 'r', encoding='utf-8') as file:
                template = Template(file.read())
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            self.wfile.write(template.render(context).encode('utf-8'))
        except FileNotFoundError:
            self.send_error(404, 'File Not Found')

    def serve_static(self, static_path):
        static_file_path = os.path.join(BASE_DIR, static_path)
        try:
            with open(static_file_path, 'rb') as file:
                self.send_response(200)
                if static_path.endswith('.css'):
                    self.send_header('Content-type', 'text/css')
                self.end_headers()
                self.wfile.write(file.read())
        except FileNotFoundError:
            self.send_error(404, 'File Not Found')

    def set_cookie(self, key, value):
        cookie = http.cookies.SimpleCookie()
        cookie[key] = value
        self.send_header('Set-Cookie', cookie.output(header='', sep=''))

    def get_cookie(self, key):
        if "Cookie" in self.headers:
            cookie = http.cookies.SimpleCookie(self.headers["Cookie"])
            if key in cookie:
                return cookie[key].value
        return None

    def check_auth_and_serve_template(self, template_name):
        username = self.get_cookie('username')
        if username:
            conn = psycopg2.connect(
                dbname=DB_NAME,
                user=DB_USER,
                password=DB_PASSWORD,
                host=DB_HOST,
                port=DB_PORT
            )
            cursor = conn.cursor()
            cursor.execute("SELECT full_name, date_of_birth, phone FROM patients")
            patients = cursor.fetchall()
            cursor.close()
            conn.close()
            patients_list = [{'full_name': p[0], 'date_of_birth': p[1], 'phone': p[2]} for p in patients]
            self.serve_template(template_name, {'patients': patients_list})
        else:
            self.send_response(302)
            self.send_header('Location', '/login')
            self.end_headers()
    def check_patient (self, template_name):
        username = self.get_cookie('username')
        if username:
            conn = psycopg2.connect(
                dbname=DB_NAME,
                user=DB_USER,
                password=DB_PASSWORD,
                host=DB_HOST,
                port=DB_PORT
            )
            cursor = conn.cursor()
            cursor.execute("SELECT full_name, date_of_birth, phone FROM patients WHERE username = %s", (username,))
            patient = cursor.fetchone()
            cursor.close()
            conn.close()
            if patient:
                context = {'username': username, 'patients': [{'full_name': patient[0], 'date_of_birth': patient[1], 'phone': patient[2]}]}
                self.serve_template(template_name, context)
            else:
                self.send_error(404, 'Patient Not Found')
        else:
            self.send_response(302)
            self.send_header('Location', '/login')
            self.end_headers()

def run(server_class=HTTPServer, handler_class=SimpleHTTPRequestHandler):
    server_address = ('', 8000)
    httpd = server_class(server_address, handler_class)
    print('Running server on port 8000...')
    httpd.serve_forever()

if __name__ == '__main__':
    run()

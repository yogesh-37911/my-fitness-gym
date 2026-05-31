"""
GymPro — Gym Membership Management System
Run: python app.py
"""

from app import create_app

app = create_app()

if __name__ == '__main__':
    print("\n" + "="*50)
    print("  GymPro — Gym Membership Management System")
    print("="*50)
    print("  URL:       http://127.0.0.1:5000")
    print("  Default PIN: 1234")
    print("="*50 + "\n")
    app.run(debug=True, host='0.0.0.0', port=5000)

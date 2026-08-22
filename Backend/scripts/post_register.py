import requests
r = requests.post('http://127.0.0.1:5000/api/auth/register', json={
    'name':'External Python',
    'email':'externalpython@example.com',
    'password':'SecurePass123!abc'
})
print(r.status_code)
print(r.text)

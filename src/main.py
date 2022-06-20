

import smtplib

def prompt(prompt):
    return input(prompt).strip()


gmail_user = 'jc.callu@gmail.com'
gmail_password = prompt('Password: ')

try:
    server = smtplib.SMTP_SSL('smtp.gmail.com', 465)
    server.ehlo()
    server.login(gmail_user, gmail_password)
except:
    print('Could not log in...')

fromaddr = gmail_user
toaddrs  = prompt("To: ").split()
print("Enter message, end with ^D (Unix) or ^Z (Windows):")

# Add the From: and To: headers at the start!
msg = ("From: %s\r\nTo: %s\r\n\r\n"
       % (fromaddr, ", ".join(toaddrs)))
while True:
    try:
        line = input()
    except EOFError:
        break
    if not line:
        break
    msg = msg + line

print("Message length is", len(msg))

server.set_debuglevel(1)
server.sendmail(fromaddr, toaddrs, msg)
server.quit()

# py-mail-templates

## Features

### Invoice subcommand

- Env:
    - SMTP_HOST
    - SMTP_USERNAME
    - SMTP_PASSWORD
    - GOCARDLESS_USER...
- Inputs:
    - CSV (name, email, invoice number, payment date, item line, price, payment method, gocardless mandate id, ...)
- Outputs:
    - CSV (...all input fields, email status code, email date, gocardless payment id)

- Application will:
    - Render an email and add a pdf to the output folder
    - Send an email with a formatted attachment to each recipient
    - Send out a summary email back to the original "SMTP_USERNAME"

### Reconciliation sub-command

- Env:
    - GOCARDLESS_USER...
- Inputs:
    - CSV (gocardless payment id, gocardless status, ...)
- Outputs:
    - CSV (... all input fields, gocardless status, date, amount, outstanding amount)

- Application will:
    - Query each payment id and save
        - gocardless payment status
        - gocardless payment date
        - gocardless payment amoun
        - outstanding amount  
    - Output a summary detail for all new payments
    - Generate a new CSV file

## TODO:

- [x] MVP: send text email through google smtp
- [x] MVP: sending HTML email
- [x] MVP: send PDF as attachment
- [x] MVP: Generate email from google doc export to html
- [x] MVP: Generate pdf from google doc export to html
- [x] MVP: Add template placeholder to google doc export
- [x] MVP: Get template placeholder data from CSV file
    - Name
    - Email
    - Invoice number
    - Current date
    - Item line (1, 2, 3 children, price)
    - Payment term (GoCardless, bank transfer)
    - Extra metadata: GoCardless mandate  

- [ ] Invoice number and gocardless mandate id should be saved together to simplify matching. Use [pandas](https://towardsdatascience.com/read-data-from-google-sheets-into-pandas-without-the-google-sheets-api-5c468536550) to generate/send emails and payment requests. Output updated state in a new CSV file to upload to drive
- [ ]
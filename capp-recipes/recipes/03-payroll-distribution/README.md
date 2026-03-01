# Recipe 03: Payroll Distribution Agent

## Business Problem
A company with employees across Nigeria, Kenya, and Ghana running payroll faces: multiple bank accounts, manual FX conversion, different settlement times per country, and zero consolidated audit trail. This recipe takes a standard payroll CSV and an agent handles the rest—optimal routing per corridor, compliance reporting per transaction, and a payroll summary report on completion.

## How It Works
1. **Reads CSV**: Parses employee details and payment amounts.
2. **Batches**: Groups payments by corridor for routing efficiency.
3. **Preflight**: Validates sufficient total balance exists across chains.
4. **Executes**: Runs payments in parallel and handles retries.
5. **Reports**: Outputs a summary CSV with success status and transaction IDs.

## Prerequisites
- `capp-sdk`
- `CAPP_API_KEY` set in environment

## Quickstart
```bash
cd recipes/03-payroll-distribution
pip install -r requirements.txt
python agent.py
```
*(A Jupyter notebook version, `agent.ipynb`, is also included for finance teams who prefer interactive environments.)*

## Input Format (`payroll.csv`)
```csv
employee_id,name,wallet_address,amount_usd,target_currency,corridor
EMP001,Amara Okafor,0xabc...111,2400,NGN,NG-KE
EMP002,David Kimani,0xdef...222,1800,KES,NG-KE
EMP003,Ama Asante,0xghi...333,2100,GHS,GH-NG
```

## Extending This Recipe
- Fetch payroll data directly from an HR API (e.g. Workday or local HRIS) instead of CSV.
- Add an email integration to send payslips with transaction receipts to employees.
- Connect to an ERP (e.g. NetSuite, Xero) to automatically reconcile the completed payroll run.

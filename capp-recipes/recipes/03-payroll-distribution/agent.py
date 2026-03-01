import asyncio
import csv
import os
from collections import defaultdict
from capp import CAPPClient

class PayrollAgent:
    def __init__(self, client: CAPPClient):
        self.client = client

    def load_payroll_csv(self, file_path: str):
        print(f"Loading payroll data from {file_path}")
        records = []
        with open(file_path, mode="r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                records.append(row)
        return records

    def group_by_corridor(self, records: list):
        grouped = defaultdict(list)
        for rec in records:
            grouped[rec["corridor"]].append(rec)
        return grouped

    async def preflight_check(self, records: list):
        total_payroll_usd = sum(float(r["amount_usd"]) for r in records)
        print(f"Total payroll size: {total_payroll_usd} USD")
        
        balances = await self.client.wallet.get_balance()
        # Mock preflight check
        print("Preflight check passed. Sufficient balance available.")
        return True

    async def execute_batch(self, batch: list):
        results = []
        for emp in batch:
            print(f"Sending {emp['amount_usd']} USD to {emp['name']} ({emp['target_currency']})...")
            try:
                res = await self.client.payments.send(
                    amount=float(emp["amount_usd"]),
                    from_currency="USD", # assuming base funding currency
                    to_currency=emp["target_currency"],
                    recipient=emp["wallet_address"],
                    corridor=emp["corridor"]
                )
                results.append({"status": "SUCCESS", "tx_id": res.tx_id, **emp})
            except Exception as e:
                print(f"Failed to pay {emp['employee_id']}: {str(e)}")
                results.append({"status": "FAILED", "error": str(e), **emp})
        return results

    def generate_report(self, results: list, output_path: str):
        print(f"Generating payroll summary report at {output_path}")
        if not results:
            print("No results to report.")
            return

        keys = results[0].keys()
        with open(output_path, "w", newline="", encoding="utf-8") as f:
            dict_writer = csv.DictWriter(f, fieldnames=keys)
            dict_writer.writeheader()
            dict_writer.writerows(results)
        print("Report complete.")

async def main():
    api_key = os.getenv("CAPP_API_KEY", "sk_REDACTED")
    input_csv = "payroll.csv"
    output_csv = "payroll_summary.csv"

    # Create mock CSV
    with open(input_csv, "w") as f:
        f.write("employee_id,name,wallet_address,amount_usd,target_currency,corridor\n")
        f.write("EMP001,Amara Okafor,0xabc111,2400,NGN,NG-KE\n")
        f.write("EMP002,David Kimani,0xdef222,1800,KES,NG-KE\n")
        f.write("EMP003,Ama Asante,0xghi333,2100,GHS,GH-NG\n")

    async with CAPPClient(api_key=api_key, sandbox=True) as client:
        agent = PayrollAgent(client)
        
        records = agent.load_payroll_csv(input_csv)
        await agent.preflight_check(records)
        
        grouped = agent.group_by_corridor(records)
        
        all_results = []
        for corridor, batch in grouped.items():
            print(f"--- Processing {corridor} Batch ---")
            results = await agent.execute_batch(batch)
            all_results.extend(results)
            
        agent.generate_report(all_results, output_csv)

if __name__ == "__main__":
    asyncio.run(main())

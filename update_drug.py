from agents.shared import supabase
import sys
import random

if not supabase:
    print("No Supabase client available.")
    sys.exit(1)

# Fetch a drug to update
response = supabase.table("drugs").select("id, stock_quantity").limit(1).execute()
if not response.data:
    print("No drugs found.")
    sys.exit(1)

drug = response.data[0]
new_qty = drug['stock_quantity'] + 1

print(f"Updating drug {drug['id']} stock from {drug['stock_quantity']} to {new_qty}...")
supabase.table("drugs").update({"stock_quantity": new_qty}).eq("id", drug['id']).execute()
print("Update complete.")

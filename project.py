from fastapi import FastAPI, HTTPException, Form, Query
from pydantic import BaseModel
from pymongo import MongoClient
from datetime import datetime,timezone
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import smtplib
from typing import List,Optional
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # You can specify a list of allowed origins if needed, e.g., ["http://localhost:3000"]
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods (GET, POST, etc.)
    allow_headers=["*"],  # Allows all headers
)

# MongoDB Connection
client = MongoClient("mongodb://localhost:27017")
db = client.stock_management
products_collection = db.products
sales_collection = db.sales
customers_collection = db.customers
installations_collection = db.installations
returns_collection = db.returns
stock_log = db.stock_log

# Product Model
class Product(BaseModel):
    product_id: str
    name: str
    category: str
    stock_quantity: int
    threshold: int
    supplier: str
    added_by: str

# Product Model
class ProductUpdate(BaseModel):
    product_name: str  # Updated to use product name
    quantity: int  # Quantity to update
    updated_by: str

# Customer Information Model
class CustomerInfo(BaseModel):
    name: str
    number: str
    address: str
    manager_name: str

# Product Information Model
class ProductInfo(BaseModel):
    product_name: str
    quantity: int
    amount: float
    remarks: str

# Sale Record Model
class SaleRecord(BaseModel):
    customer: CustomerInfo
    product_names: List[str]
    quantities: List[int]
    amounts: List[float]
    remarks: List[str]
    date: str
    total_amount: float

# Installation Record Model
class InstallationRecord(BaseModel):
    staff_names: List[str]  # List of staff members involved in the installation
    manager_name: str  # Manager overseeing the installation
    customer_name: str
    customer_number: str
    customer_address: str
    installation_date: str
    products: List[str]  # List of products installed
    quantities: List[int]  # List of quantities for each product
    remarks: List[str]  # Remarks for each product installation

# Return Model
class ReturnRequest(BaseModel):
    staff_name: str
    manager_name: str
    customer_name: str
    customer_number: str
    customer_address: str
    return_date: str
    products: List[str]
    quantities: List[int]
    remarks: str

# Email setup (Gmail SMTP server)
SENDER_EMAIL = "gamingidofmine@gmail.com"  # Replace with your Gmail address
SENDER_PASSWORD = "onoi wwnf vxql xscx"  # Replace with your Gmail app password
RECIPIENT_EMAIL = "sahil14agrawal03@gmail.com"  # Replace with your phone or email address
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587

# Helper function to send an email
def send_email(subject: str, message: str):
    msg = MIMEMultipart()
    msg['From'] = SENDER_EMAIL
    msg['To'] = RECIPIENT_EMAIL
    msg['Subject'] = subject

    msg.attach(MIMEText(message, 'plain'))

    try:
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()  # Secure the connection
        server.login(SENDER_EMAIL, SENDER_PASSWORD)
        text = msg.as_string()
        server.sendmail(SENDER_EMAIL, RECIPIENT_EMAIL, text)
        server.quit()
        print("Email sent successfully!")
    except Exception as e:
        print(f"Error sending email: {e}")

def convert_objectid_to_str(log):
    log["_id"] = str(log["_id"])  # Convert ObjectId to string
    return log

@app.post("/add-product/")
async def add_product(product: Product):
    if products_collection.find_one({"product_id": product.product_id}):
        raise HTTPException(status_code=400, detail="Product with this ID already exists")

    new_product = product.model_dump()
    new_product["date_added"] = datetime.now(timezone.utc)
    result = products_collection.insert_one(new_product)
    
    if result.acknowledged:
        # Fetch updated stock info
        product_info = products_collection.find_one({"product_id": product.product_id})

        # Prepare email content
        email_subject = "New Product Added to Inventory"
        email_body = (
            f"Product: {product.name}\n"
            f"Category: {product.category}\n"
            f"Quantity Added: {product.stock_quantity}\n"
            f"Supplier: {product.supplier}\n"
            f"Added By: {product.added_by}\n"
            f"Date Added: {product_info['date_added']}\n"
            f"Current Stock: {product_info['stock_quantity']}\n"
        )

        # Send email
        send_email(email_subject, email_body)

        # Log the action in stock_log collection
        stock_log_entry = {
            "date": datetime.now(timezone.utc).isoformat(),
            "action": "add",
            "product_id": product.product_id,
            "product_name": product.name,
            "quantity_changed": product.stock_quantity,
            "remaining_stock": product_info['stock_quantity'],
            "performed_by": product.added_by
        }
        stock_log.insert_one(stock_log_entry)

        return {"message": "Product added successfully, logged and email notification sent!"}
    
    else:
        raise HTTPException(status_code=500, detail="Failed to add product")

@app.get("/view-all-stock/", response_model=List[Product])
async def view_all_stock():
    products = list(products_collection.find())  # Fetch all products
    if not products:
        raise HTTPException(status_code=404, detail="No products found.")
    
    # Convert the MongoDB _id to string
    for product in products:
        product['_id'] = str(product['_id'])
    
    return products

@app.put("/update-product-quantity/")
async def update_product_quantity(product_update: ProductUpdate):
    # Find the product by product name (field is 'name' in the DB)
    product = products_collection.find_one({"name": product_update.product_name})
    
    if not product:
        raise HTTPException(status_code=404, detail="Product not found.")
    
    # Calculate the new stock quantity
    new_quantity = product["stock_quantity"] + product_update.quantity
    if new_quantity < 0:
        raise HTTPException(status_code=400, detail="Quantity cannot be negative.")

    # Update the product stock
    result = products_collection.update_one(
        {"name": product_update.product_name},
        {"$set": {"stock_quantity": new_quantity, "date_added": datetime.now(timezone.utc)}}
    )

    if result.modified_count == 1:
        # Prepare email content
        email_subject = f"Product Quantity Updated: {product['name']}"
        email_body = (
            f"Product: {product['name']}\n"
            f"Category: {product['category']}\n"
            f"Old Stock Quantity: {product['stock_quantity']}\n"
            f"Quantity Added: {product_update.quantity}\n"
            f"New Stock Quantity: {new_quantity}\n"
            f"Updated By: {product_update.updated_by}\n"
            f"Update Date: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')}\n"
        )

        # Send email notification
        send_email(email_subject, email_body)

        # Log the update in stock_log collection
        stock_log_entry = {
            "date": datetime.now(timezone.utc).isoformat(),
            "action": "update",
            "product_id": product["product_id"],
            "product_name": product["name"],
            "quantity_changed": product_update.quantity,
            "remaining_stock": new_quantity,
            "performed_by": product_update.updated_by
        }
        stock_log.insert_one(stock_log_entry)

        return {"message": f"Product quantity updated successfully. New stock: {new_quantity}"}
    else:
        raise HTTPException(status_code=500, detail="Failed to update product quantity.")

@app.post("/record-sale/")
async def record_sale(
    customer_name: str = Form(...),
    customer_number: str = Form(...),
    customer_address: str = Form(...),
    manager_name: str = Form(...),
    date: str = Form(...),
    total_amount: float = Form(...),
    product_names: List[str] = Form(...),
    quantities: List[int] = Form(...),
    amounts: List[float] = Form(...),
    remarks: List[str] = Form(...),
):
    # Check if customer already exists in the database
    customer = customers_collection.find_one({"name": customer_name, "number": customer_number})

    if not customer:
        # If customer doesn't exist, create a new customer entry
        customer_data = {
            "name": customer_name,
            "number": customer_number,
            "address": customer_address,
            "date_added": datetime.now()
        }
        customers_collection.insert_one(customer_data)

    # Ensure the number of product details matches
    if len(product_names) != len(quantities) or len(product_names) != len(amounts) or len(product_names) != len(remarks):
        raise HTTPException(status_code=400, detail="Mismatch in the number of products and details provided.")

    # Prepare the sale record for insertion
    sale_record = {
        "customer_name": customer_name,
        "customer_number": customer_number,
        "customer_address": customer_address,
        "manager_name": manager_name,
        "date": date,
        "total_amount": total_amount,
        "products": [],
        "date_added": datetime.now()
    }

    # Loop through products to process them
    for product_name, quantity, amount, remark in zip(product_names, quantities, amounts, remarks):
        # Add product details to the sale record
        sale_record["products"].append({
            "product_name": product_name,
            "quantity": quantity,
            "amount": amount,
            "remarks": remark
        })

        # Update stock quantity of the product in the inventory
        product_in_db = products_collection.find_one({"name": product_name})
        if product_in_db:
            new_stock_quantity = product_in_db['stock_quantity'] - quantity
            if new_stock_quantity < 0:
                raise HTTPException(status_code=400, detail=f"Not enough stock for {product_name}")

            # Update the product quantity in the products collection
            products_collection.update_one(
                {"name": product_name},
                {"$set": {"stock_quantity": new_stock_quantity}}
            )

            # Log the sale in the stock_log collection
            stock_log_entry = {
                "date": datetime.now(timezone.utc).isoformat(),
                "action": "sale",
                "product_id": product_in_db["product_id"],
                "product_name": product_name,
                "quantity_changed": -quantity,
                "remaining_stock": new_stock_quantity,
                "performed_by": manager_name,
                "customer_name": customer_name
            }
            stock_log.insert_one(stock_log_entry)
        else:
            raise HTTPException(status_code=404, detail=f"Product {product_name} not found in inventory.")

    # Insert the sale record into the sales collection
    sale_result = sales_collection.insert_one(sale_record)

    # Create email message body
    email_message = f"Sale Information:\n\nCustomer: {customer_name}\nManager: {manager_name}\nDate: {date}\nTotal Amount: {total_amount}\n\n"
    email_message += "Products Sold:\n"
    for product_name, quantity, amount, remark in zip(product_names, quantities, amounts, remarks):
        email_message += f"Product: {product_name}\nQuantity: {quantity}\nAmount: {amount}\nRemarks: {remark}\n\n"
    
    # Send email notification
    send_email("New Sale Notification", email_message)

    return {"message": "Sale recorded successfully", "sale_id": str(sale_result.inserted_id)}

@app.post("/record-installation/")
async def record_installation(
    staff_names: List[str] = Form(...),
    manager_name: str = Form(...),
    customer_name: str = Form(...),
    customer_number: str = Form(...),
    customer_address: str = Form(...),
    installation_date: str = Form(...),
    products: List[str] = Form(...),
    quantities: List[int] = Form(...),
    remarks: List[str] = Form(...),
):
    # Check if customer exists in the database
    customer = customers_collection.find_one({"name": customer_name, "number": customer_number})

    if not customer:
        # If customer doesn't exist, create a new customer entry
        customer_data = {
            "name": customer_name,
            "number": customer_number,
            "address": customer_address,
            "date_added": datetime.now()
        }
        customers_collection.insert_one(customer_data)

    # Ensure the number of product details matches
    if len(products) != len(quantities) or len(products) != len(remarks):
        raise HTTPException(status_code=400, detail="Mismatch in the number of products and details provided.")

    # Prepare the installation record for insertion
    installation_record = {
        "staff_names": staff_names,
        "manager_name": manager_name,
        "customer_name": customer_name,
        "customer_number": customer_number,
        "customer_address": customer_address,
        "installation_date": installation_date,
        "products": [],
        "date_added": datetime.now()
    }

    # Loop through products to process them
    for product, quantity, remark in zip(products, quantities, remarks):
        # Add product details to the installation record
        installation_record["products"].append({
            "product_name": product,
            "quantity": quantity,
            "remarks": remark
        })

        # Update stock quantity of the product in the inventory
        product_in_db = products_collection.find_one({"name": product})
        if product_in_db:
            new_stock_quantity = product_in_db['stock_quantity'] - quantity
            if new_stock_quantity < 0:
                raise HTTPException(status_code=400, detail=f"Not enough stock for {product}")

            # Update the product quantity in the products collection
            products_collection.update_one(
                {"name": product},
                {"$set": {"stock_quantity": new_stock_quantity}}
            )

            # Log the installation action in the stock_log collection
            stock_log_entry = {
                "date": datetime.now(timezone.utc).isoformat(),
                "action": "installation",
                "product_id": product_in_db["product_id"],
                "product_name": product,
                "quantity_changed": -quantity,
                "remaining_stock": new_stock_quantity,
                "performed_by": manager_name,
                "customer_name": customer_name
            }
            stock_log.insert_one(stock_log_entry)
        else:
            raise HTTPException(status_code=404, detail=f"Product {product} not found in inventory.")

    # Insert the installation record into the installations collection
    installation_result = installations_collection.insert_one(installation_record)

    # Create email message body
    email_message = f"Installation Information:\n\nCustomer: {customer_name}\nManager: {manager_name}\nDate: {installation_date}\n\n"
    email_message += "Products Installed:\n"
    for product, quantity, remark in zip(products, quantities, remarks):
        email_message += f"Product: {product}\nQuantity: {quantity}\nRemarks: {remark}\n\n"

    # Send email notification
    send_email("New Installation Notification", email_message)

    return {"message": "Installation recorded successfully", "installation_id": str(installation_result.inserted_id)}

@app.post("/return-item/")
async def return_item(
    staff_name: str = Form(...),
    manager_name: str = Form(...),
    customer_name: str = Form(...),
    customer_number: str = Form(...),
    customer_address: str = Form(...),
    return_date: str = Form(...),
    products: List[str] = Form(...),
    quantities: List[int] = Form(...),
    remarks: str = Form(...),
):
    if len(products) != len(quantities):
        raise HTTPException(status_code=400, detail="Products and quantities list lengths must match.")

    # Check if customer exists
    customer = customers_collection.find_one({
        "name": customer_name,
        "number": customer_number
    })

    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found.")

    email_message = (
        f"Return Record:\n\n"
        f"Customer: {customer_name}\n"
        f"Phone: {customer_number}\n"
        f"Address: {customer_address}\n"
        f"Staff: {staff_name}\n"
        f"Manager: {manager_name}\n"
        f"Date: {return_date}\n"
        f"Remarks: {remarks}\n\n"
    )

    # Loop through products and update stock
    for product, quantity in zip(products, quantities):
        product_in_db = products_collection.find_one({"name": product})

        if not product_in_db:
            raise HTTPException(status_code=404, detail=f"Product '{product}' not found in inventory.")

        # Update the stock by adding the returned quantity
        new_stock_quantity = product_in_db['stock_quantity'] + quantity
        products_collection.update_one(
            {"name": product},
            {"$set": {"stock_quantity": new_stock_quantity}}
        )

        # Log the return action in the stock_log collection
        stock_log_entry = {
            "date": datetime.now(timezone.utc).isoformat(),
            "action": "return",
            "product_id": product_in_db["product_id"],
            "product_name": product,
            "quantity_changed": quantity,
            "remaining_stock": new_stock_quantity,
            "performed_by": manager_name,
            "customer_name": customer_name
        }
        stock_log.insert_one(stock_log_entry)

        # Record return details for each product
        return_record = {
            "staff_name": staff_name,
            "manager_name": manager_name,
            "customer_name": customer_name,
            "customer_number": customer_number,
            "customer_address": customer_address,
            "return_date": return_date,
            "product_name": product,
            "quantity": quantity,
            "remarks": remarks,
            "date_added": datetime.now()
        }

        returns_collection.insert_one(return_record)

        email_message += (f"Product: {product}\n"
                          f"Quantity Returned: {quantity}\n"
                          f"Updated Stock: {new_stock_quantity}\n\n")

    send_email("Product Return Notification", email_message)

    return {
        "message": "Products returned successfully.",
        "products": products,
        "quantities": quantities
    }

@app.get("/view-logs/")
async def view_logs(action: Optional[str] = Query(None, regex="^(add|update|sale|installation|return)$")):
    # Build query based on action
    query = {}
    if action:
        query["action"] = action
    
    # Query for logs based on the action
    logs_cursor = stock_log.find(query)
    logs = list(logs_cursor)
    
    if not logs:
        raise HTTPException(status_code=404, detail=f"No logs found for action '{action}'." if action else "No logs found.")

    # Convert ObjectId to string for all logs
    logs = [convert_objectid_to_str(log) for log in logs]

    return {"logs": logs}

@app.get("/view-records/")
async def view_records(record_type: str):
    if record_type == "sale":
        # Fetch all sales records
        sales_cursor = sales_collection.find()
        sales = list(sales_cursor)

        if not sales:
            raise HTTPException(status_code=404, detail="No sales records found.")

        # Convert ObjectId to string for all sales records
        for sale in sales:
            sale["_id"] = str(sale["_id"])

        return {"sales": sales}
    
    elif record_type == "installation":
        # Fetch all installation records
        installations_cursor = installations_collection.find()
        installations = list(installations_cursor)

        if not installations:
            raise HTTPException(status_code=404, detail="No installation records found.")

        # Convert ObjectId to string for all installations records
        for installation in installations:
            installation["_id"] = str(installation["_id"])

        return {"installations": installations}
    
    elif record_type == "return":
    # Fetch all return records
        returns_cursor = returns_collection.find()
        returns = list(returns_cursor)

        if not returns:
            raise HTTPException(status_code=404, detail="No return records found.")

        # Convert ObjectId to string for all return records
        for return_record in returns:
            return_record["_id"] = str(return_record["_id"])

        return {"returns": returns}
    
    else:
        raise HTTPException(status_code=400, detail="Invalid record type. Use 'sale' or 'installation'.")

@app.get("/search-customer")
def search_customer(
    name: Optional[str] = Query(None), 
    number: Optional[str] = Query(None)
):
    if not name and not number:
        raise HTTPException(status_code=400, detail="Please provide either name or number")

    query = {}
    if name:
        query["customer_name"] = {'$regex': name, '$options': 'i'}
    if number:
        query["customer_number"] = number

    sales = list(sales_collection.find(query))
    installations = list(installations_collection.find(query))
    returns = list(returns_collection.find(query))

    # Prepare response
    response = []

    for sale in sales:
        response.append({
            "customer_id": str(sale.get("_id")),
            "customer_name": sale.get("customer_name"),
            "customer_phone": sale.get("customer_number"),
            "product_name": [product.get("product_name") for product in sale.get("products", [])],
            "quantity": [product.get("quantity") for product in sale.get("products", [])],
            "total_amount": sale.get("total_amount"),
            "date": sale.get("date"),
            "action": "Sale"
        })

    for installation in installations:
        response.append({
            "customer_id": str(installation.get("_id")),
            "customer_name": installation.get("customer_name"),
            "customer_phone": installation.get("customer_number"),
            "product_name": installation.get("products"),
            "date": installation.get("installation_date"),
            "action": "Installation"
        })
    
    for return_data in returns:
        response.append({
            "customer_id": str(return_data.get("_id")),
            "customer_name": return_data.get("customer_name"),
            "customer_phone": return_data.get("customer_number"),
            "product_name": return_data.get("product_name"),
            "quantity": return_data.get("quantity"),
            "date": return_data.get("return_date"),
            "action": "Return"
            })

    if not response:
        raise HTTPException(status_code=404, detail="No records found")

    return response

@app.get("/get-products/")
async def get_products():
    try:
        products = products_collection.find({}, {"name": 1, "_id": 1})
        product_list = [{"id": str(product["_id"]), "name": product["name"]} for product in products]
        
        if not product_list:
            raise HTTPException(status_code=404, detail="No products found.")
        
        return product_list
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching products: {str(e)}")

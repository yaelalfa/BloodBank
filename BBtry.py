import tkinter as tk
from tkinter import IntVar, LabelFrame, Radiobutton, messagebox
from tkinter import ttk, filedialog
from PIL import Image, ImageTk
import firebase_admin
from firebase_admin import credentials, db, auth
from datetime import datetime
import pandas as pd
import datetime
from tkcalendar import Calendar
import re










# Initialize Firebase
cred = credentials.Certificate("bloodbank-d5818-firebase-adminsdk-xo681-56855b8026.json")
firebase_admin.initialize_app(cred, {
    'databaseURL': 'https://bloodbank-d5818-default-rtdb.firebaseio.com/'
})

# Initialize stock table with some values if empty
def create_db():
    hospitals = {
        'Soroka University Medical Center': {
            'bloodStock': {
                'A+': 10, 'O+': 10, 'B+': 10, 'AB+': 10,
                'A-': 10, 'O-': 10, 'B-': 10, 'AB-': 10
            }
        },
        'Barzilai Medical Center': {
            'bloodStock': {
                'A+': 10, 'O+': 10, 'B+': 10, 'AB+': 10,
                'A-': 10, 'O-': 10, 'B-': 10, 'AB-': 10
            }
        },
        'Yoseftal Medical Center': {
            'bloodStock': {
                'A+': 10, 'O+': 10, 'B+': 10, 'AB+': 10,
                'A-': 10, 'O-': 10, 'B-': 10, 'AB-': 10
            }
        },
        'Assuta Ashdod University Hospital': {
            'bloodStock': {
                'A+': 10, 'O+': 10, 'B+': 10, 'AB+': 10,
                'A-': 10, 'O-': 10, 'B-': 10, 'AB-': 10
            }
        }
    }

    ref = db.reference('hospital_stock')  # Change to 'hospitals' for multiple hospitals
    existing_hospitals = ref.get()

    if not existing_hospitals:
        ref.set(hospitals)


create_db()

#---------------------------------------------------------------------------------------------------------------------------------

def log_audit_trail(action, table_name, details):
    timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    audit_ref = db.reference('audit_trail')
    audit_ref.push({
        'action': action,
        'table_name': table_name,
        'timestamp': timestamp,
        'details': details
    })

#---------------------------------------------------------------------------------------------------------------------------------

#ניפוי מנות דם פגי תוקף

def remove_old_donations():
    cutoff_date = datetime.datetime.now() - datetime.timedelta(days=30)
    donations_ref = db.reference("donations")  # Reference to the 'donations' table

    # Retrieve all donations
    donations = donations_ref.get()
    
    if donations:
        for donation_key, donation in donations.items():
            # Extract the donation date
            donation_date = datetime.datetime.strptime(donation['donation_date'], '%Y-%m-%d')

            # Check if the donation date is older than the cutoff date
            if donation_date < cutoff_date:
                # Extract donor details and donation info
                donor_name = donation.get('donor_name', 'Unknown')
                donor_id = donation.get('donor_id', 'Unknown')
                blood_type = donation.get('blood_type', 'Unknown')
                donation_units = donation.get('donation_units', 'Unknown')

                # Log the removal of the donation to audit trail
                log_audit_trail('Remove Donation', 'donations', 
                                f'Donor {donor_name} (ID: {donor_id}) donated {donation_units} units of {blood_type} blood. Donation removed due to expiration.')

                # Delete the old donation from the database
                donations_ref.child(donation_key).delete()


#---------------------------------------------------------------------------------------------------------------------------------
# Alert when blood stock is low 

def check_blood_stock():
    # Reference to the hospital stock data
    hospitals_ref = db.reference('hospital_stock')
    low_stock_types = []

    # Fetching all hospitals
    hospitals_data = hospitals_ref.get() or {}

    # Iterate through each hospital's blood stock
    for hospital_id, blood_stock_data in hospitals_data.items():
        if 'bloodStock' in blood_stock_data:
            blood_stock = blood_stock_data['bloodStock']

            for blood_type, quantity in blood_stock.items():
                # Set the threshold for notifications
                if quantity < 10:  
                    low_stock_types.append((hospital_id, blood_type, quantity))

    # If any low stock types were found, show an alert
    if low_stock_types:
        show_alert(low_stock_types)

# Function to show alert box
def show_alert(low_stock_types):
    alert_message = "Low Stock Alert:\n\n"
    for hospital_id, blood_type, quantity in low_stock_types:
        alert_message += f"Hospital ID: {hospital_id}, Blood Type: {blood_type}: {quantity}\n"

    messagebox.showwarning("Alert", alert_message)

def add_message_to_mailbox(user_id, subject, content):
    try:
        # Reference the mailbox of the user
        ref = db.reference(f'mailbox/{user_id}')
        
        # Create the mailbox node if it doesn't exist
        ref.set({})  # This initializes the mailbox structure if it does not exist
        
        # Create a new message reference
        new_message_ref = ref.push()  # Create a unique ID for the new message
        
        # Set the message details
        new_message_ref.set({
            'subject': subject,
            'content': content,
            'read': False  # Message starts as "unread"
        })
        print("Message added successfully.")
    except Exception as e:
        print(f"Error adding message to mailbox: {e}")

#---------------------------------------------------------------------------------------------------------------------------------
# Blood donation interface
def donate_blood():
    def submit_donation():
        blood_type = blood_type_var.get()
        donation_date = donation_date_entry.get()
        donor_id = donor_id_entry.get()
        donor_name = donor_name_entry.get()
        donation_units = units_scale.get()
        hospital = hospital_var.get()

        # Validate the donation date format
        try:
            datetime.datetime.strptime(donation_date, "%Y-%m-%d")
        except ValueError:
            messagebox.showerror("Error", "Invalid date format. Please use YYYY-MM-DD.")
            return

        donations_ref = db.reference('donations')
        new_donation = {
            'blood_type': blood_type,
            'donation_date': donation_date,
            'donor_id': donor_id,
            'donor_name': donor_name,
            'units': donation_units,
            'hospital':hospital
        }
        donations_ref.push(new_donation)

        stock_ref =db.reference(f'hospital_stock/{hospital}/bloodStock/{blood_type}')


        current_units = stock_ref.get() or 0
        stock_ref.set(current_units + donation_units)

        log_audit_trail('New Donation', 'donations', f'Donor {donor_name} (ID: {donor_id}) donated {donation_units} units of {blood_type} blood to {hospital}.')
        log_audit_trail('Update Stock', 'hospital_stock', f'{donation_units} units added to {hospital} stock.')

        messagebox.showinfo("Success", "Donation recorded successfully!")
        donate_window.destroy()

    donate_window = tk.Toplevel(bg="white")
    donate_window.title("Blood Donation")
    donate_window.geometry("400x400")
    donate_window.resizable(False, False)

    blood_type_var = tk.StringVar()
    tk.Label(donate_window, text="Enter Donation", font=('Helvetica', 18,'bold'), fg='#6C0707',bg="white").grid(row=0, column=0, padx=30, pady=10, sticky='w')

    tk.Label(donate_window, text="Blood Type:", font=('Helvetica', 12),bg="white").grid(row=1, column=0, padx=10, pady=5, sticky='w')
    blood_type_var = tk.StringVar(value="A+")
    blood_type_menu = ttk.Combobox(donate_window, textvariable=blood_type_var, values=["A+", "O+", "B+", "AB+", "A-", "O-", "B-", "AB-"])
    blood_type_menu.grid(row=1, column=1, padx=10, pady=5, sticky='w')

    tk.Label(donate_window, text="Donation Date (YYYY-MM-DD):", font=('Helvetica', 12),bg="white").grid(row=2, column=0, padx=10, pady=5, sticky='w')
    donation_date_entry = tk.Entry(donate_window)
    donation_date_entry.grid(row=2, column=1, padx=10, pady=5, sticky='w')

    tk.Label(donate_window, text="Donor ID:", font=('Helvetica', 12),bg="white").grid(row=3, column=0, padx=10, pady=5, sticky='w')
    donor_id_entry = tk.Entry(donate_window)
    donor_id_entry.grid(row=3, column=1, padx=10, pady=5, sticky='w')

    tk.Label(donate_window, text="Donor Name:", font=('Helvetica', 12),bg="white").grid(row=4, column=0, padx=10, pady=5, sticky='w')
    donor_name_entry = tk.Entry(donate_window)
    donor_name_entry.grid(row=4, column=1, padx=10, pady=5, sticky='w')

    tk.Label(donate_window, text="Units to Donate:", font=('Helvetica', 12),bg="white").grid(row=5, column=0, padx=10, pady=5, sticky='w')
    units_scale = tk.Scale(donate_window, from_=1, to=10, orient=tk.HORIZONTAL,bg="white")
    units_scale.grid(row=5, column=1, padx=10, pady=5, sticky='w')

    tk.Label(donate_window, text="Select where to Donate:", font=('Helvetica', 12),bg="white").grid(row=6, column=0, padx=10, pady=5, sticky='w')
    hospital_var = tk.StringVar(value="Yoseftal Medical Center")
    hospital_menu = ttk.Combobox(donate_window, textvariable=hospital_var, values= [
        "Soroka University Medical Center", "Barzilai Medical Center", "Yoseftal Medical Center", "Assuta Ashdod University Hospital"
    ])
    hospital_menu.grid(row=6, column=1, padx=10, pady=5, sticky='w')

    button_frame = tk.Frame(donate_window,bg="white")
    button_frame.grid(row=7, column=0, columnspan=2, pady=20, sticky='w')

    submit_button = tk.Button(button_frame, text="Submit Donation", command=submit_donation, bg="#F49386", fg="#030100", font=('Helvetica', 12))
    submit_button.grid(row=0, column=0, padx=10)

    cancel_button = tk.Button(button_frame, text="Cancel Donation", command=donate_window.destroy, bg="#8c8c8c", fg="black", font=('Helvetica', 12))
    cancel_button.grid(row=0, column=1, padx=10)

#---------------------------------------------------------------------------------------------------------------------------------


# Blood for Operating rooms interface
def dispense_blood():
    def update_units_label(*args):
        blood_type = blood_type_var.get()
        hospital=hospital_var.get()
        stock_ref =db.reference(f'hospital_stock/{hospital}/bloodStock/{blood_type}')
        stock = stock_ref.get() or 0
        units_label.config(text=f"Available units: {stock}")

        # Update the alternative units
        alternative_units = get_alternative_units(blood_type,hospital)
        formatted_alternatives = format_alternative_units(alternative_units)
        alternatives_label.config(text=f"Alternative units:\n{formatted_alternatives}")

    def format_alternative_units(alternative_units):
        alternatives = alternative_units.split(", ")
        formatted_alternatives = ""
        for i in range(0, len(alternatives), 4):
            row = ", ".join(alternatives[i:i+4])
            formatted_alternatives += row + "\n"
        return formatted_alternatives.strip()

    def submit_dispense():
        blood_type = blood_type_var.get()
        needed_units = int(units_entry.get())
        hospital=hospital_var.get()
        stock_ref =db.reference(f'hospital_stock/{hospital}/bloodStock/{blood_type}')
        current_units = stock_ref.get() or 0

        if current_units >= needed_units:
            stock_ref.set(current_units - needed_units)
            log_audit_trail('Dispensed', 'hospital_stock', f'{needed_units} units of {blood_type} blood dispensed from {hospital}.')

            messagebox.showinfo("Success", f"Dispensed {needed_units} units of {blood_type} blood from {hospital}.")
            update_units_label()
        else:
            remaining_units = needed_units - current_units
            alternative_units = get_alternative_units_dict(blood_type,hospital)
            total_available_units = current_units

            # Interactive selection of alternative units
            alternative_window = tk.Toplevel(dispense_window, bg="white")
            alternative_window.title("Select Alternative Units")
            alternative_window.geometry("490x500")
            
            tk.Label(alternative_window, text=f"You requested {needed_units} units of {blood_type} blood.", font=('Helvetica', 13),bg="white").pack()
            tk.Label(alternative_window, text=f"Unfortunately, we only have {total_available_units} units available.", font=('Helvetica', 13),bg="white").pack()
            tk.Label(alternative_window, text=f"Please choose the remaining {remaining_units} units from the alternatives below:", font=('Helvetica', 13),bg="white").pack()

            selected_alternatives = {}
            for alt_type, alt_units in alternative_units.items():
                tk.Label(alternative_window, text=f"{alt_type} (Available: {alt_units}):", font=('Helvetica', 12),bg="white").pack()
                alt_entry = tk.Entry(alternative_window)
                alt_entry.insert(0, '0')  # Set the default value to '0'
                alt_entry.pack()
                selected_alternatives[alt_type] = alt_entry

            def submit_alternatives():
                nonlocal total_available_units
                total_selected_units = 0
                dispensed_details = []  # To hold details of dispensed blood types and their quantities

                for alt_type, alt_entry in selected_alternatives.items():
                    alt_needed_units = int(alt_entry.get())
                    total_selected_units += alt_needed_units
                    dispensed_details.append(f"{alt_needed_units} units of {alt_type}")  # Store details

                total_available_units += total_selected_units

                if total_available_units >= needed_units:
                    stock_ref.set(0)  # Assuming this indicates that the primary stock is depleted
                    for alt_type, alt_entry in selected_alternatives.items():
                        alt_needed_units = int(alt_entry.get())
                        alt_stock_ref = db.reference(f'hospital_stock/{hospital}/bloodStock/{alt_type}')
                        alt_stock_ref.set(alt_stock_ref.get() - alt_needed_units)

                    # Construct the message to include how much of each type was dispensed
                    dispensed_message = ", ".join(dispensed_details)
                    messagebox.showinfo("Success", f"Dispensed {needed_units} units using {blood_type} and alternatives: {dispensed_message}.")
                    
                    alternative_window.destroy()
                    log_audit_trail('Dispensed', 'blood_stock', f'{needed_units} units of {blood_type} blood dispensed using alternatives: {dispensed_message}.')
                    update_units_label()
                else:
                    messagebox.showerror("Error", f"Insufficient units after considering alternatives. Only {total_available_units} units available.")

            tk.Button(alternative_window, text="Submit Alternatives", command=submit_alternatives, bg="#F49386", fg="#030100", font=('Helvetica', 12)).pack(pady=15)
            tk.Button(alternative_window, text="Cancel", command=alternative_window.destroy, bg="#8c8c8c", fg="black", font=('Helvetica', 12)).pack(pady=15)

        check_blood_stock()

    def get_alternative_units_dict(blood_type,hospital):
        compatible_types = {
            'A+': ['A-', 'O+', 'O-'],
            'O+': ['O-'],
            'B+': ['B-', 'O+', 'O-'],
            'AB+': ['A+', 'A-', 'B+', 'B-', 'AB-', 'O+', 'O-'],
            'A-': ['O-'],
            'O-': [],
            'B-': ['O-'],
            'AB-': ['A-', 'B-', 'O-']
        }
        alternatives = {}
        for compatible in compatible_types[blood_type]:
            ref =db.reference(f'hospital_stock/{hospital}/bloodStock/{compatible}')
            alternatives[compatible] = ref.get() or 0
        return alternatives

    def get_alternative_units(blood_type,hospital):
        alternatives = get_alternative_units_dict(blood_type,hospital)
        alternative_units = ", ".join([f"{k}: {v}" for k, v in alternatives.items()])
        return alternative_units
 
    dispense_window = tk.Toplevel(bg="white")
    dispense_window.title("Blood Dispensation")
    dispense_window.geometry("470x470")
    tk.Label(dispense_window, text="Blood Dispensation", font=('Helvetica',18,"bold"), fg='#6C0707',bg="white").grid(row=0, column=0, padx=20, pady=10, sticky='w')

    tk.Label(dispense_window, text="Hospital Name:", font=('Helvetica', 14),bg="white").grid(row=1, column=0, padx=20, pady=10, sticky='w')
    hospital_var = tk.StringVar(value="Choose hospital")  # Default value, can be modified
    hospital_menu = ttk.Combobox(dispense_window, textvariable=hospital_var, values=[
        "Soroka University Medical Center", 
        "Barzilai Medical Center", 
        "Yoseftal Medical Center", 
        "Assuta Ashdod University Hospital"
    ])
    hospital_menu.grid(row=1, column=1, padx=10, pady=10, sticky='w')
    hospital_var.trace_add('write', update_units_label)

    tk.Label(dispense_window, text="Blood Type:", font=('Helvetica', 14),bg="white").grid(row=2, column=0, padx=20, pady=10, sticky='w')
    blood_type_var = tk.StringVar(value="A+")
    blood_type_menu = ttk.Combobox(dispense_window, textvariable=blood_type_var, values=["A+", "O+", "B+", "AB+", "A-", "O-", "B-", "AB-"])
    blood_type_menu.grid(row=2, column=1, padx=10, pady=10, sticky='w')
    blood_type_var.trace_add('write', update_units_label)

    units_label = tk.Label(dispense_window, text="Available units: 0", font=('Helvetica', 14),bg="white")
    units_label.grid(row=3, column=0, padx=20, pady=10, sticky='w')

    alternatives_label = tk.Label(dispense_window, text="Alternative units: N/A", font=('Helvetica', 14),bg="white")
    alternatives_label.grid(row=4, column=0, padx=20, pady=10, sticky='w')

    tk.Label(dispense_window, text="Units to Dispense:", font=('Helvetica', 14),bg="white").grid(row=5, column=0, padx=20, pady=10, sticky='w')
    units_entry = tk.Entry(dispense_window)
    units_entry.grid(row=5, column=1, padx=10, pady=10, sticky='w')

    submit_button = tk.Button(dispense_window, text="Submit Dispensation", command=submit_dispense, bg="#F49386", fg="#030100", font=('Helvetica', 12))
    submit_button.grid(row=6, column=0, columnspan=2, padx=20, pady=20)
    tk.Button(dispense_window, text="Cancel", command=dispense_window.destroy, bg="#8c8c8c", fg="black", font=('Helvetica', 12)).grid(row=7, column=0, columnspan=2)


    update_units_label()

#---------------------------------------------------------------------------------------------------------------------------------


def emergency_dispense():
    def submit_emergency():
        # Get the selected hospital from the Combobox
        selected_hospital = hospital_var.get()

        if not selected_hospital:  # Check if no hospital is selected
            messagebox.showerror("Error", "Please select a hospital.")
            return

        # Reference to the O- blood type in Firebase for the selected hospital
        o_negative_ref = db.reference(f'hospital_stock/{selected_hospital}/bloodStock/O-')
        stock = o_negative_ref.get()

        if stock and stock > 0:
            # Set the units of O- blood to 0
            o_negative_ref.set(0)
            log_audit_trail('Emergency Dispense', 'blood_stock', f'{stock} units of O- blood dispensed in emergency from {selected_hospital}.')
            messagebox.showinfo("Success", f"Dispensed {stock} units of O- blood from {selected_hospital}.")
            emergency_window.destroy()
        else:
            messagebox.showerror("Error", f"No O- blood units available in {selected_hospital}.")

    emergency_window = tk.Toplevel(bg="white")
    emergency_window.title("Blood for Emergencies")
    emergency_window.geometry("440x300")

    tk.Label(emergency_window, text="Emergency Dispense", font=('Helvetica',18,"bold"), fg='#6C0707',bg="white").pack(pady=10)

    # Fetch list of hospitals from Firebase
    hospitals_ref = db.reference('hospital_stock')
    hospitals = hospitals_ref.get() or {}
    hospital_list = list(hospitals.keys())

    # Variable to store the selected hospital
    hospital_var = tk.StringVar(emergency_window)

    tk.Label(emergency_window, text="Select Hospital:", font=('Helvetica', 12),bg="white").pack(pady=10)
    
    # Creating a Combobox
    hospital_combobox = ttk.Combobox(emergency_window, textvariable=hospital_var, values=hospital_list, state="readonly")
    hospital_combobox.pack(pady=10)
    hospital_combobox.set("Select a hospital")  # Default placeholder text

    tk.Button(emergency_window, text="Dispense O-", command=submit_emergency, bg="#F49386", fg="#030100", font=('Helvetica', 12)).pack(pady=20)
    tk.Button(emergency_window, text="Cancel", command=emergency_window.destroy, bg="#8c8c8c", fg="black", font=('Helvetica', 12)).pack(pady=5)
    tk.Label(emergency_window, text="**All the O- blood will be dispensed from the selected hospital", font=('Helvetica', 11),bg="white").pack(pady=10)


#---------------------------------------------------------------------------------------------------------------------------------



def show_donation_table(treeview):
    ref = db.reference('donations')
    donations = ref.get()

    # Clear the existing data in the Treeview
    for row in treeview.get_children():
        treeview.delete(row)

    # Populate the Treeview with data from Firebase
    if donations:
        for donation_id, donation_data in donations.items():

            # Extract data from each donation record
            blood_type = donation_data.get('blood_type', 'N/A')
            donation_date = donation_data.get('donation_date', 'N/A')
            donor_id = donation_data.get('donor_id', 'N/A')
            donor_name = donation_data.get('donor_name', 'N/A')
            units = donation_data.get('units', 'N/A')
            
            # Insert data into Treeview
            treeview.insert("", "end", values=( blood_type, donation_date, donor_id, donor_name, units))

def show_log_table(treeview):
    ref = db.reference('audit_trail')
    logs = ref.get()

    # Clear the existing data in the Treeview
    for row in treeview.get_children():
        treeview.delete(row)

    # Populate the Treeview with data from Firebase
    if logs:
        for log_id, log_data in logs.items():
            # Extract data from each log record
            action = log_data.get('action', 'N/A')
            table_name = log_data.get('table_name', 'N/A')
            timestamp = log_data.get('timestamp', 'N/A')
            details = log_data.get('details', 'N/A')
            
            # Insert data into Treeview
            treeview.insert("", "end", values=( action, table_name, timestamp, details))

def show_tables():

    def export_data(treeview, filename):
        columns = treeview["columns"]
        data = [treeview.item(row)["values"] for row in treeview.get_children()]
        df = pd.DataFrame(data, columns=columns)
        df.to_excel(filename, index=False)
         

     
    def on_export(notebook,table1,table2):
            # Determine which tab is currently selected
            selected_tab = notebook.index(notebook.select())
            # Determine file format based on user choice
            filetype = filedialog.asksaveasfilename(defaultextension=".xlsx")
            
            if not filetype:
                return

            # Export data based on the selected tab
            if selected_tab == 0:
                export_data(table1, filetype )
            elif selected_tab == 1:
                export_data(table2, filetype)


    def setup_tabs(notebook):
        # Create frames for each tab
        table1_frame = ttk.Frame(notebook)
        table2_frame = ttk.Frame(notebook)

        # Add frames to notebook as tabs
        notebook.add(table1_frame, text="Audit log")
        notebook.add(table2_frame, text="Donation Info")

        # Create Table 1 (Audit Log)
        table1 = ttk.Treeview(table1_frame, columns=( "Action", "Table Name", "Timestamp", "Details"), show='headings')
        table1.heading("Action", text="Action")
        table1.heading("Table Name", text="Table Name")
        table1.heading("Timestamp", text="Timestamp")
        table1.heading("Details", text="Details")

        table1.pack(fill="both", expand=True, padx=10, pady=10)

        table1.column("Action", width=80)  # Set width for Blood Type column
        table1.column("Table Name", width=90)  # Set width for Donation Date column
        table1.column("Timestamp", width=100)  # Set width for Donor ID column
        table1.column("Details", width=150)  # Set width for Donor Name column
        
        # Populate Table 1 with data
        show_log_table(table1)

        # Create Table 2 (Donations)
        table2 = ttk.Treeview(table2_frame, columns=( "Blood Type", "Donation Date", "Donor ID", "Donor Name", "Units"), show='headings')
        table2.heading("Blood Type", text="Blood Type")
        table2.heading("Donation Date", text="Donation Date")
        table2.heading("Donor ID", text="Donor ID")
        table2.heading("Donor Name", text="Donor Name")
        table2.heading("Units", text="Units")

        table2.column("Blood Type", width=80)  # Set width for Blood Type column
        table2.column("Donation Date", width=150)  # Set width for Donation Date column
        table2.column("Donor ID", width=100)  # Set width for Donor ID column
        table2.column("Donor Name", width=100)  # Set width for Donor Name column
        table2.column("Units", width=80)
        table2.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Populate Table 2 with data
        show_donation_table(table2)
        but = tk.Button(tables_window, text="Export to Excel", 
                command=lambda: on_export(notebook, table1, table2), 
                bg="#8c8c8c", fg="black", font=('Helvetica', 11))
        but.pack(side="right", pady=10, padx=5)

    # Create main window
    tables_window = tk.Toplevel(bg="white")
    tables_window.title("Tables")
    tables_window.geometry("600x400")
    
    if user_role=="research student":
        label=tk.Label(tables_window, text="Welcome Research student!", font=('Helvetica', 18, 'bold'), fg='#6C0707',bg="white")
        label.pack(side="top", pady=10)  # Pack the label on top with padding

        notebook = ttk.Notebook(tables_window)
        notebook.pack(fill="both", expand=True, padx=10, pady=10)  # Fill the remaining space and add padding

    else:
        label = tk.Label(tables_window, text="Details", font=('Helvetica', 18, 'bold'), fg='#6C0707',bg="white")
        label.pack(side="top", pady=10)  # Pack the label on top with padding
        # Create Notebook widget
        notebook = ttk.Notebook(tables_window)
        notebook.pack(fill="both", expand=True, padx=10, pady=10)  # Fill the remaining space and add padding
        but=tk.Button(tables_window, text="Close", command=tables_window.destroy, bg="#8c8c8c", fg="black", font=('Helvetica', 11))
        but.pack(side="left", padx=5,pady=10)



    setup_tabs(notebook)

#---------------------------------------------------------------------------------------------------------------------------------
# manage user window setup


def get_non_admin_users():
    ref = db.reference('users')
    users = ref.get()
    non_admin_users = []

    if users:
        for user_id, user_data in users.items():
            role = user_data.get('role', '')
            if role != 'admin':
                non_admin_users.append(user_data.get('username', 'Unknown'))

    return non_admin_users

###################

def delete_user(username):
    username=username.get()
    ref = db.reference('users')
    users = ref.get()
    if users:
        for user_id, user_data in users.items():
            if user_data.get('username', '') == username:
                ref.child(user_id).delete()
                # Show success messagebox
                messagebox.showinfo("Success", f"User '{username}' has been successfully deleted.")
                return True
    return False

###################

def manage_user_window():
    manage_window = tk.Toplevel(root, bg="white")
    manage_window.title("Manage Users")
    manage_window.geometry("600x400")

    # Header Label
    tk.Label(manage_window, text="Add new user", font=('Helvetica', 13, 'bold'), bg="white", fg='#6C0707').grid(row=0, column=0, sticky='w', pady=5)

    # Username Entry
    tk.Label(manage_window, text="Username:", font=('Helvetica', 12), bg="white").grid(row=1, column=0, sticky='w', padx=20, pady=10)
    username_entry = tk.Entry(manage_window)
    username_entry.grid(row=1, column=1, sticky='w', pady=10)

    # Password Entry
    tk.Label(manage_window, text="Password:", font=('Helvetica', 12), bg="white").grid(row=2, column=0, sticky='w', padx=20, pady=10)
    password_entry = tk.Entry(manage_window, show="*")
    password_entry.grid(row=2, column=1, sticky='w', pady=10)

    role_chosen = tk.StringVar()

    # Role Label and Combobox
    tk.Label(manage_window, text="Role:", font=('Helvetica', 12), bg="white").grid(row=1, column=2, sticky='w', padx=40, pady=20)

    roles = ['User', 'Research student']
    role_combobox = ttk.Combobox(manage_window, textvariable=role_chosen, values=roles, state='readonly')
    role_combobox.grid(row=2, column=2, padx=10, pady=10)
    role_combobox.set("Select a role")

    # Register Button
    tk.Button(manage_window, text="Register new user", command=lambda: register_user(username_entry.get(), password_entry.get(), role_chosen.get(), manage_window), font=('Helvetica', 10)).grid(row=3, column=1, sticky='EW', padx=40, pady=5)

    # First Separator
    separator = ttk.Separator(manage_window, orient='horizontal')
    separator.place(relx=0, rely=0.47, relwidth=1)

    # Remove User Section
    tk.Label(manage_window, text="Remove user", font=('Helvetica', 13, 'bold'), bg="white", fg='#6C0707').grid(row=7, column=0, sticky='W', pady=20)

    user_to_remove = tk.StringVar(value="Choose user")
    users = get_non_admin_users()
    user_combobox = ttk.Combobox(manage_window, textvariable=user_to_remove, values=users)
    user_combobox.grid(row=8, column=1, sticky='W', pady=20)

    # Delete Button
    tk.Button(manage_window, text="Delete", command=lambda: delete_user(user_to_remove.get()), font=('Helvetica', 10)).grid(row=8, column=2, sticky='EW', pady=5)

    # Second Separator
    separator2 = ttk.Separator(manage_window, orient='horizontal')
    separator2.place(relx=0, rely=0.78, relwidth=1)

    # Return Button
    tk.Button(manage_window, text="Return to menu", command=manage_window.destroy, font=('Helvetica', 10)).grid(row=13, column=0, padx=30, sticky='ew', pady=30)

    manage_window.mainloop()





###################


def register_user(username, password, chosen_role, window):
    if not username or not password or not chosen_role or chosen_role=="Select a role":
        messagebox.showwarning("Input Error", "All fields must be filled out.")
        return
    role=chosen_role
    
    ref = db.reference('users')
    users = ref.get()

    if users:
        for user_id, user_data in users.items():
            if user_data.get('username') == username:
                messagebox.showwarning("Registration Error", "Username already exists.")
                return
    
    user_ref = ref.push({
        'username': username,
        'password': password,
        'role': role
    })

    messagebox.showinfo("Success", "User registered successfully!")
    window.destroy()  # Close the registration window

#---------------------------------------------------------------------------------------------------------------------------------
#   Blood tranfer window



def blood_transfer_window():

    def execute_transfer():
        blood_type = blood_type_var.get()
        source=from_hospital_var.get()
        dest=dest_hospital_var.get()
        units= int(units_entry.get())
        source_ref= db.reference(f'hospital_stock/{source}/bloodStock/{blood_type}')
        stock = source_ref.get() or 0
        if units>stock:
            messagebox.showerror("Error", "The chosen quantity is bigger that the stock, choose a lower number.")
            return
        source_ref.set(stock-units)
        update_stock_label
        dest_ref= db.reference(f'hospital_stock/{dest}/bloodStock/{blood_type}')
        stock = dest_ref.get() or 0
        dest_ref.set(stock+units)
        
            

        
        log_audit_trail('Transfer Blood', 'hospital_stock', f'Source hospital: {source} , Destination hospital: {dest}, {units} units of {blood_type}.')
        main_frame.destroy()
        messagebox.showinfo("Success", f"Tansfer Success.")
        


        
    
    main_frame = tk.Toplevel(root, bg='white')
    
    tk.Label(main_frame, text="Blood Transfer", font=('Helvetica', 14, 'bold'), bg="white", fg='#6C0707').grid(row=1, column=0, padx=10, pady=5, sticky='w')
    tk.Label(main_frame, text="From where to transfer the blood:", font=('Helvetica', 12), bg="white").grid(row=2, column=0, padx=10, pady=5, sticky='w')

    hospitals_list = [
        "Soroka University Medical Center", 
        "Barzilai Medical Center", 
        "Yoseftal Medical Center", 
        "Assuta Ashdod University Hospital"
    ]

    # "From" hospital ComboBox
    from_hospital_var = tk.StringVar(value="")
    from_hospital_menu = ttk.Combobox(main_frame, textvariable=from_hospital_var, values=hospitals_list)
    from_hospital_menu.grid(row=2, column=1, padx=10, pady=5, sticky='w')

    tk.Label(main_frame, text="Choose blood type to transfer:", font=('Helvetica', 12), bg="white").grid(row=3, column=0, padx=10, pady=5, sticky='w')

    blood_type_var = tk.StringVar(value="A+")
    blood_type_menu = ttk.Combobox(main_frame, textvariable=blood_type_var, values=["A+", "O+", "B+", "AB+", "A-", "O-", "B-", "AB-"])
    blood_type_menu.grid(row=3, column=1, padx=10, pady=5, sticky='w')

    units_label = tk.Label(main_frame, text="How many units do you want to transfer: ", bg="white", font=('Helvetica', 12))
    units_label.grid(row=4, column=0, padx=10, pady=10, sticky="w")
    units_entry = tk.Entry(main_frame, width=30)
    units_entry.grid(row=4, column=1, padx=10, pady=10)

    stock_title_label = tk.Label(main_frame, text="Selected Hospital Blood Type Inventory", font=('Helvetica', 12), bg="white")
    stock_title_label.grid(row=5, column=0, padx=10, pady=5, sticky='w')

    stock_label = tk.Label(main_frame, text="   ", font=('Helvetica', 11), bg="white")
    stock_label.grid(row=5, column=1, padx=10, pady=5, sticky='w')

    # Function to update stock label based on selected blood type and hospital
    def update_stock_label(*args):
        hospitals_ref = db.reference('hospital_stock')
        hospitals_data = hospitals_ref.get() or {}

        selected_hospital = from_hospital_var.get()
        selected_blood_type = blood_type_var.get()

        if selected_hospital and selected_blood_type:
            blood_stock = hospitals_data.get(selected_hospital, {}).get('bloodStock', {})
            quantity = blood_stock.get(selected_blood_type, "Not available")
            stock_label.config(text=f"{selected_blood_type}: {quantity}")

    # Function to update destination hospital list, excluding the selected "from" hospital
    def update_destination_hospitals(*args):
        print("** ", from_hospital_var.get())
        selected_from_hospital = from_hospital_var.get()
        available_hospitals = [h for h in hospitals_list if h != selected_from_hospital]
        dest_hospital_menu['values'] = available_hospitals
        if dest_hospital_var.get() == selected_from_hospital:
            dest_hospital_var.set("")  # Clear selection if the same hospital is selected
        dest_hospital_menu.configure(values=available_hospitals)

    # Bind updates for hospital selection and blood type selection
    from_hospital_menu.bind("<<ComboboxSelected>>", update_destination_hospitals)
    from_hospital_menu.bind("<<ComboboxSelected>>", update_stock_label)
    blood_type_menu.bind("<<ComboboxSelected>>", update_stock_label)

    # Call the update function initially to display the stock for the default selection
    update_stock_label()
    

    # Destination hospital ComboBox
    tk.Label(main_frame, text="Destination hospital:", font=('Helvetica', 12), bg="white").grid(row=6, column=0, padx=10, pady=5, sticky='w')

    dest_hospital_var = tk.StringVar()
    dest_hospital_menu = ttk.Combobox(main_frame, textvariable=dest_hospital_var)
    dest_hospital_menu.grid(row=6, column=1, padx=10, pady=5, sticky='w')

    # Initially update the destination hospitals
    update_destination_hospitals()

    tk.Button(main_frame, text="Transfer", command=execute_transfer, bg="#F49386", fg="#030100", font=('Helvetica', 12)).grid(row=7, column=0, padx=10, pady=5, sticky='w')

    cancel_button = tk.Button(main_frame, text="Cancel Blood Transfer", command=main_frame.destroy, bg="#8c8c8c", fg="black", font=('Helvetica', 12))
    cancel_button.grid(row=7, column=1, padx=10)



    






#---------------------------------------------------------------------------------------------------------------------------------
# Main window setup
def clear_root_widgets():
    for widget in root.winfo_children():
        widget.destroy()

def clear_main_widgets():
    for widget in root.winfo_children():
        widget.destroy()
    on_create(root)



def show_main_window(user_name):
    # Create the main window
    clear_root_widgets()  # Clear existing widgets
    
    main_frame = tk.Frame(root, bg='white')
    main_frame.pack(pady=0)

    header_frame = tk.Frame(main_frame, bg='white')
    header_frame.pack(side="top", fill='x')
    if user_role == 'admin':
        image = Image.open("mail-icon.png")
        image = image.resize((30, 30))
        photo = ImageTk.PhotoImage(image)
        
        # Create a frame to align the icon to the right
        image_label = tk.Label(header_frame, image=photo, bg='white', bd=0)
        image_label.image = photo  # Keep a reference to avoid garbage collection
        image_label.pack(side="right",  pady=10)  # Pack it to the right side of the header frame


    tk.Label(main_frame, text=f"Welcome {user_name}, What would you like to do?", font=('Helvetica', 14, 'bold'), fg='#6C0707',bg='white').pack( anchor='w', pady=20)

    button_frame = tk.Frame(main_frame,bg='white')
    button_frame.pack(pady=0)
    tk.Button(button_frame, text="Blood Donation", command=donate_blood, bg="#F49386", fg="#030100", font=('Helvetica', 12)).pack(pady=10)
    tk.Button(button_frame, text="Blood for Operating Rooms", command=dispense_blood, bg="#F49386", fg="#030100", font=('Helvetica', 12)).pack(pady=10)
    tk.Button(button_frame, text="Blood for Emergencies", command=emergency_dispense, bg="#F49386", fg="#030100", font=('Helvetica', 12)).pack(pady=10)
    if(user_role=="admin"):
       tk.Button(button_frame, text="Browse Tables info", command=show_tables, bg="#FFC8C1", fg="#030100", height=0, font=('Helvetica', 12)).pack(pady=10,padx=30)
       tk.Button(button_frame, text="Manage users", command=manage_user_window, bg="#FFC8C1", fg="#030100", height=0, font=('Helvetica', 12)).pack(pady=10,padx=30)
       tk.Button(button_frame, text="Blood Transfer", command=blood_transfer_window, bg="#FFC8C1", fg="#030100", height=0, font=('Helvetica', 12)).pack(pady=10,padx=30)
    if(user_role=="User"):
        tk.Button(button_frame, text="Blood Transfer", command=blood_transfer_window, bg="#FFC8C1", fg="#030100", height=0, font=('Helvetica', 12)).pack(pady=10,padx=30)


    tk.Button(main_frame, text="Log out", command=clear_main_widgets, bg="#8c8c8c", fg="black", font=('Helvetica', 12)).pack(pady=10,padx=30)


#---------------------------------------------------------------------------------------------------------------------------------
#Donor main window


def show_calendar():


    # Function to display the calendar and time selection
    def submit_appointment():
        # Get the selected date and time
        donation_date = cal.get_date()
        parsed_date = datetime.datetime.strptime(donation_date, "%m/%d/%y")
         # Format to dd/mm/yyyy
        formatted_donation_date = parsed_date.strftime("%d/%m/%y")
        donation_time_str = time_combobox.get()
        hospital_chosen = hospital_combobox.get()
          
        
        if donation_time_str == "Select Time":
            messagebox.showerror("Error", "Please select a time.")
        elif hospital_chosen == "Select Hospital":
            messagebox.showerror("Error", "Please select hospital.")
        else:
            # Get the current date and time
            donation_time = datetime.datetime.strptime(donation_time_str, '%I:%M %p').time()
            current_datetime = datetime.datetime.now()
            donation_datetime = datetime.datetime.combine(parsed_date.date(), donation_time)
            # Check if the appointment time has already passed
            if parsed_date < current_datetime and current_datetime>donation_datetime:
                    messagebox.showerror("Error", "The selected date and time has already passed.")
            else:    
                ref = db.reference('appointments')
                bookings = ref.get()
                ref2 = db.reference('donation_history')
                donation_history = ref2.get()
                
                if bookings:
                    for booing_id, booking_data in bookings.items():

                        if booking_data.get('id') == user_id:
                            messagebox.showwarning("Error", "You already have an appointment.")
                            return
                        elif booking_data.get('hospital') == hospital_chosen and booking_data.get('time') == donation_time:
                            messagebox.showwarning("Error", "This time slot is already booked. Please choose a different date or time.")
                            return
                
                bookings = ref.push({
                    'hospital': hospital_chosen,
                    'date': formatted_donation_date,
                    'time': donation_time_str, 
                    'id': user_id
                })
                donation_history = ref2.push({
                    'hospital': hospital_chosen,
                    'date': formatted_donation_date,  
                    'time': donation_time_str,  
                    'id': user_id
                })
                # Action to book the appointment
                messagebox.showinfo("Appointment Booked", f"Your appointment for {donation_date} at {donation_time} has been booked.")
                # Optionally, hide the calendar and time widgets after booking
                donor_window.destroy()
                cal.pack_forget()
                time_combobox.pack_forget()
                hospital_combobox.pack_forget()
                submit_button.pack_forget()
                donor()

            
    # Create the main window for donor management

    donor_window = tk.Toplevel(root,bg="white")
    donor_window.title("Book Donation Appointment")
    donor_window.geometry("400x550")

    tk.Label(donor_window, text="Book Donation Appointment", font=('Arial', 16,'bold'),bg="white",fg='#6C0707').pack(pady=10)
    

    calendar_label = tk.Label(donor_window, text="Select Donation Date:", font=('Arial', 12),bg="white")
    calendar_label.pack(pady=10)
    current_time=datetime.datetime.now()
    cal = Calendar(donor_window, selectmode='day', year=current_time.year, month=current_time.month, day=current_time.day)
    cal.pack(pady=10)

    time_label = tk.Label(donor_window, text="Select Donation Time:", font=('Arial', 12),bg="white")
    time_label.pack(pady=10)

    time_options = [
        "09:00 AM", "10:00 AM", "11:00 AM", "12:00 PM", "01:00 PM", 
        "02:00 PM", "03:00 PM", "04:00 PM", "05:00 PM"
    ]
    hospital_options = [
        "Soroka University Medical Center", "Barzilai Medical Center", "Yoseftal Medical Center", "Assuta Ashdod University Hospital"
    ]

    time_combobox = ttk.Combobox(donor_window, values=time_options, state="readonly")
    time_combobox.set("Select Time")
    time_combobox.pack(pady=10)

    time_label = tk.Label(donor_window, text="Select Hospital to donate to:", font=('Arial', 12),bg="white")
    time_label.pack(pady=10)

    hospital_combobox = ttk.Combobox(donor_window, values=hospital_options, state="readonly")
    hospital_combobox.set("Select Hospital")
    hospital_combobox.pack(pady=10)


    
    return_button = tk.Button(donor_window, text="Return to menu", command=donor_window.destroy)
    return_button.pack(side=tk.LEFT, padx=10, pady=20)  # Add padding for space between buttons
    # Submit button for appointment
    submit_button = tk.Button(donor_window, text="Submit Appointment", command=submit_appointment, width=110)
    submit_button.pack(side=tk.LEFT, padx=50, pady=20)  # Add padding for space between buttons


def donor():

    global no_appointments_label  # Declare as global to update later


    def check_appointments():
        ref = db.reference('appointments')
        bookings = ref.get()
        user_has_appointment = False
        
        if bookings:
            for appt_id, appt_data in bookings.items():
                if appt_data.get('id', 'N/A') == user_id:
                    user_has_appointment = True
                    messagebox.showwarning("Error", "You already have an appointment. \nPlease cancel your current appointment before booking a new one.")
                    break
        
        # If the user doesn't have an appointment, allow them to book one
        if not user_has_appointment:
            show_calendar()

    def cancel_appointment():
        ref = db.reference('appointments')
        bookings = ref.get()
        if bookings:
           for appt_id, appt_data in bookings.items():
               if appt_data.get('id', 'N/A') == user_id:
                    ref.child(appt_id).delete()
                    messagebox.showinfo("Success", "Appointment canceled successfully!")
                    no_appointments_label.config(text="No appointments found.")

                    donor()
                    break
    clear_root_widgets()  # Clear existing widgets
    donor_window = tk.Frame(root, bg='white')
    donor_window.pack(pady=0)
    #donor_window.geometry("400x00")
    ref = db.reference('appointments')
    appt = ref.get()
    title="Hello "+user_name+ "!"
    tk.Label(donor_window, text=title, font=('Arial', 20, 'bold'),bg='white',fg='#6C0707').pack(pady=20)
    # Button to show the calendar and appointment booking directly
    tk.Button(donor_window, text="Book Donation Appointment", command=check_appointments).pack(pady=15)

    # Button to view donation history
    tk.Button(donor_window, text="View Donation History", command=view_donation_history).pack(pady=10)


    check_if_found=0
    if appt:
        for appt_id, appt_data in appt.items():
            # Extract data from each log record
            hospital = appt_data.get('hospital', 'N/A')
            time = appt_data.get('time', 'N/A')
            date = appt_data.get('date', 'N/A')
            check_id = appt_data.get('id', 'N/A')
            if(check_id==user_id):
                tk.Label(donor_window, text="You have an appointment", font=('Arial', 15, 'bold'),bg='white',fg='#6C0707').pack(pady=20,anchor='e')
                check_if_found=1
                tk.Label(donor_window, text="Appointment Details:",bg='white').pack()
                tk.Label(donor_window, text=f"Hospital: {hospital}",bg='white').pack()
                tk.Label(donor_window, text=f"Date: {date}",bg='white').pack()
                tk.Label(donor_window, text=f"Time: {time}",bg='white').pack()
                tk.Button(donor_window, text="Cancel appointment", command=cancel_appointment).pack(pady=20)
    if check_if_found == 0:
        no_appointments_label = tk.Label(donor_window, text="No appointments found.", bg='white', fg='#6C0707')
        no_appointments_label.pack()
    else:
        no_appointments_label = tk.Label(donor_window, text="", bg='white')  # Empty label if there is an appointment
     
    

    tk.Button(donor_window, text="Log out", command=clear_main_widgets, bg="#8c8c8c", fg="black", font=('Helvetica', 12)).pack(pady=10)

def extract_data_from_details(details):
    # Regular expression pattern to match ID, amount, and blood type
    pattern = r"ID:\s*(\d+).*?(\d+)\s+units\s+of\s+(\w+\+|\w+-|\w+)"
    
    # Search for the pattern in the donation detail
    match = re.search(pattern, details)

    if match:
        # Extracting ID, amount, and blood type from the matched groups
        donor_id = match.group(1)      # Extracted ID
        amount = int(match.group(2))    # Extracted amount (convert to integer)
        blood_type = match.group(3)     # Extracted blood type
        
        return donor_id, amount, blood_type
    else:
        return None, None, None  # Return None if the pattern doesn't match


def view_donation_history():
    # New window to view donation history
    history_window = tk.Toplevel(root)
    history_window.title("Donation History")
    history_window.geometry("400x300")
    history_window.configure(bg='white')
    tk.Label(history_window, text="Donation History", font=('Arial', 15, 'bold'),bg='white',fg='#6C0707').pack(pady=20)
    ref = db.reference('audit_trail')
    don = ref.get()
    former_don=0
    counter=0
    if don:
        for don_id, don_data in don.items():
            # Extract data from each log record
            action = don_data.get('action', 'N/A')
            timestamp = don_data.get('timestamp', 'N/A')
            details = don_data.get('details', 'N/A')
            check_id = don_data.get('id', 'N/A')
            print('*****', details)
            if type(details)==str: 
                donor_id, amount, blood_type=extract_data_from_details(details)  
            if(action=='New Donation' and donor_id==user_id):
                former_don=1
                counter=counter+1
                tk.Label(history_window, text=f"Donation {counter}",bg='white').pack()
                tk.Label(history_window, text=f"Time: {timestamp}",bg='white').pack()
                tk.Label(history_window, text=f"Amount: {amount} units of {blood_type}",bg='white').pack()
                tk.Label(history_window, text="----------------------------------------",bg='white').pack()
    if(former_don==0):
        tk.Label(history_window, text="You have no donation history",bg='white').pack()

    tk.Button(history_window, text="Back", command=history_window.destroy, bg="#8c8c8c", fg="black", font=('Helvetica', 12)).pack(pady=10)

#---------------------------------------------------------------------------------------------------------------------------------
# global variables
user_role=""
user_id=""
user_name=""
def check_login(username, password):
    global user_role, user_id,user_name
    ref = db.reference('users')
    users = ref.get()
    if not username or not password:
        messagebox.showwarning("Input Error", "All fields must be filled out.")
        return
    check1 = check2 = 0
    if users:
        for user_id, user_data in users.items():
            username_inDB = user_data.get('username', 'N/A')
            password_inDB = user_data.get('password', 'N/A')
            role = user_data.get('role', 'N/A')
            if username_inDB == username:
                check1 = 1
                user_name=username
                if str(password_inDB) == password:
                    check2 = 1
                    user_role = role
                    if role == "research student":
                        show_tables()
                        return
                    elif role == "donor":
                        user_id = user_data.get('id', 'N/A')
                        donor()
                        return
                    else:
                        show_main_window(user_name=username)
                    #root.destroy()
                    return  
    if(check1==0):
        messagebox.showwarning("Login Error", "Username does not exists.")
    elif(check2==0):
        messagebox.showwarning("Login Error", "Password Incorrect.")
    return False



def register_donor(new_donor_window,full_name, id, password, con_password):
    if not full_name or not password or not id or not con_password:
        messagebox.showwarning("Input Error", "All fields must be filled out.")
        return
    
    role="donor"
    
    ref = db.reference('users')
    users = ref.get()

    if users:
        for user_id, user_data in users.items():
            if user_data.get('id') == id:
                messagebox.showwarning("Registration Error", "ID already exists.")
                return
    
    user_ref = ref.push({
        'username': full_name,
        'id': id,
        'password': password, 
        'role': role
    })
    messagebox.showinfo("Success", "User registered successfully!")
    new_donor_window.destroy()  # Close the registration window
    




def signup_new_donor():
    new_donor_window = tk.Toplevel(root)
    new_donor_window.title("Donor Sign-up")
    new_donor_window.geometry("400x300")

    title_label = tk.Label(new_donor_window,text="Donor Sign-up",font=('Helvetica', 18,'bold'),fg='#6C0707')
    title_label.grid()

    # Full Name (Label and Entry in the same row)
    full_name_label = tk.Label(new_donor_window, text="Full Name")
    full_name_label.grid(row=1, column=0, padx=10, pady=10, sticky="w")
    full_name_entry = tk.Entry(new_donor_window, width=30)
    full_name_entry.grid(row=1, column=1, padx=10, pady=10)

    # id 
    id_label = tk.Label(new_donor_window, text="ID")
    id_label.grid(row=2, column=0, padx=10, pady=10, sticky="w")
    id_entry = tk.Entry(new_donor_window, width=30)
    id_entry.grid(row=2, column=1, padx=10, pady=10)

    # Password
    password_label = tk.Label(new_donor_window, text="Password")
    password_label.grid(row=3, column=0, padx=10, pady=10, sticky="w")
    password_entry = tk.Entry(new_donor_window, show="*", width=30)
    password_entry.grid(row=3, column=1, padx=10, pady=10)

    # Confirm Password
    confirm_password_label = tk.Label(new_donor_window, text="Confirm Password")
    confirm_password_label.grid(row=4, column=0, padx=10, pady=10, sticky="w")
    confirm_password_entry = tk.Entry(new_donor_window, show="*", width=30)
    confirm_password_entry.grid(row=4, column=1, padx=10, pady=10)

    # Register Button
    register_button = tk.Button(new_donor_window, text="Register", command=lambda: register_donor(
        new_donor_window, 
        full_name_entry.get(),  # Get the text from the entry
        id_entry.get(),  # Get the text from the entry
        password_entry.get(),  # Get the text from the entry
        confirm_password_entry.get()  # Get the text from the entry
    ))
    register_button.grid(row=5, column=1, pady=20)

    

    
def on_create(root):

    # remove donations that are more than 30 days old
    remove_old_donations()

    root.title("Blood Management System")
    root.geometry("500x500")
    root.configure(bg='white')


    try:
        # Load and resize the image
        image = Image.open("donation-logo.jpg")
        image = image.resize((150, 150))
        photo = ImageTk.PhotoImage(image)
        
        # Create a frame to hold the image and the text
        frame = tk.Frame(root, bg='white')
        frame.pack(pady=30)  # Adjust the padding as needed

        # Add the image to the frame
        image_label = tk.Label(frame, image=photo, bg='white', bd=0)
        image_label.image = photo  # Keep a reference to avoid garbage collection
        image_label.pack(side="left", padx=10)  # Place on the left side with padding

        # Add the text to the frame, next to the image
        tk.Label(frame, text="Blood Bank System", font=('Helvetica', 18,'bold'), fg='#6C0707', bg='white').pack(side="left")

    except Exception as e:
        print(f"Error loading image: {e}")


    username_label = tk.Label(root, text="Username:",font=('Helvetica', 12),bg="white")
    username_label.pack()
    username_entry = tk.Entry(root)
    username_entry.pack()

    # Password label and entry
    password_label = tk.Label(root, text="Password:",font=('Helvetica', 12),bg="white")
    password_label.pack(pady=5)
    password_entry = tk.Entry(root, show="*")
    password_entry.pack(pady=5)


    # Login button
    login_button = tk.Button(root, text="Login", 
                                command=lambda: check_login(username_entry.get(), password_entry.get()))
    login_button.pack(pady=20)

    signup_button = tk.Label(root, text="First time donating blood ? Signup as a new donor", fg="#3B6ECC",bg="white",font=("Arial", 10))
    signup_button.bind("<Button-1>", lambda e:signup_new_donor())

    signup_button.pack(pady=23,anchor="w",padx=15)
    root.mainloop()

root = tk.Tk()
on_create(root)
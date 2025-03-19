import tkinter as tk
from tkinter import ttk, messagebox as mess, filedialog
import cv2
import os
import numpy as np
from PIL import Image
import datetime
import time
import mysql.connector
from mysql.connector import errorcode
from tkcalendar import DateEntry
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle
from reportlab.lib import colors

# Load environment variables for database configuration
import os
db_config = {
    'user': os.getenv('DB_USER', 'root'),
    'password': os.getenv('DB_PASSWORD', 'Karan@8087'),
    'host': os.getenv('DB_HOST', 'localhost')
}

def get_db_connection():
    return mysql.connector.connect(**db_config, database='AttendanceSystem')

def create_database():
    """Create the database and tables if they don't exist."""
    try:
        connection = mysql.connector.connect(**db_config)
        cursor = connection.cursor()

        cursor.execute("CREATE DATABASE IF NOT EXISTS AttendanceSystem")
        cursor.execute("USE AttendanceSystem")

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS StudentDetails (
            serial_no INT AUTO_INCREMENT PRIMARY KEY,
            student_id VARCHAR(50) NOT NULL,
            name VARCHAR(100) NOT NULL
        )
        """)

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS Attendance (
            id INT AUTO_INCREMENT PRIMARY KEY,
            student_id VARCHAR(50) NOT NULL,
            name VARCHAR(100) NOT NULL,
            date DATE NOT NULL,
            time TIME NOT NULL
        )
        """)

        connection.commit()
        cursor.close()
        connection.close()

    except mysql.connector.Error as err:
        handle_database_error(err)

def handle_database_error(err):
    if err.errno == errorcode.ER_ACCESS_DENIED_ERROR:
        mess.showerror(title='Database Error', message='Invalid username or password')
    elif err.errno == errorcode.ER_BAD_DB_ERROR:
        mess.showerror(title='Database Error', message='Database does not exist')
    else:
        mess.showerror(title='Database Error', message=str(err))

def assure_path_exists(path):
    if not os.path.exists(path):
        os.makedirs(path)

# Global variable to store the after ID
tick_after_id = None

def tick():
    global tick_after_id
    time_string = time.strftime('%H:%M:%S')
    clock.config(text=time_string)
    tick_after_id = clock.after(200, tick)

def on_closing():
    global tick_after_id
    if tick_after_id:
        clock.after_cancel(tick_after_id)
    window.destroy()

def contact():
    mess.showinfo(title='Contact Us', message="Please contact us on: 'support@example.com'")

def check_haarcascadefile():
    if not os.path.isfile("haarcascade_frontalface_default.xml"):
        mess.showerror(title='File Missing', message='Haarcascade file is missing. Please contact support.')
        window.destroy()

def TakeImages():
    try:
        check_haarcascadefile()
        assure_path_exists("StudentDetails/")
        assure_path_exists("TrainingImage/")

        # Ensure txt and txt2 are initialized
        if not txt or not txt2:
            mess.showerror(title='Initialization Error', message='Widgets are not initialized properly.')
            return

        Id = txt.get().strip()
        name = txt2.get().strip()
        if name.replace(" ", "").isalpha():
            cam = cv2.VideoCapture(0)
            harcascadePath = "haarcascade_frontalface_default.xml"
            detector = cv2.CascadeClassifier(harcascadePath)
            sampleNum = 0
            while True:
                ret, img = cam.read()
                if not ret:
                    break
                gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
                faces = detector.detectMultiScale(gray, 1.3, 5)
                for (x, y, w, h) in faces:
                    cv2.rectangle(img, (x, y), (x + w, y + h), (255, 0, 0), 2)
                    sampleNum += 1
                    image_path = f"TrainingImage/{name}.{Id}.{sampleNum}.jpg"
                    cv2.imwrite(image_path, gray[y:y + h, x:x + w])
                    cv2.imshow('Taking Images', img)
                if cv2.waitKey(100) & 0xFF == ord('q') or sampleNum >= 10:
                    break
            cam.release()
            cv2.destroyAllWindows()

            save_student_details(Id, name)
            res = "Images Taken for ID: " + Id
            message1.configure(text=res)
        else:
            mess.showerror(title='Invalid Name', message='Please enter a valid name (letters and spaces only).')
    except Exception as e:
        mess.showerror(title='Error', message=str(e))

def save_student_details(Id, name):
    connection = get_db_connection()
    cursor = connection.cursor()
    cursor.execute("INSERT INTO StudentDetails (student_id, name) VALUES (%s, %s)", (Id, name))
    connection.commit()
    cursor.close()
    connection.close()

def TrainImages():
    check_haarcascadefile()
    assure_path_exists("TrainingImageLabel/")
    recognizer = cv2.face.LBPHFaceRecognizer_create()
    harcascadePath = "haarcascade_frontalface_default.xml"
    detector = cv2.CascadeClassifier(harcascadePath)
    faces, IDs = getImagesAndLabels("TrainingImage")
    if len(faces) == 0:
        mess.showinfo(title='No Registrations', message='Please register someone first!')
        return
    try:
        recognizer.train(faces, np.array(IDs))
    except Exception as e:
        mess.showerror(title='Training Error', message=str(e))
        return
    recognizer.save("TrainingImageLabel/Trainner.yml")
    res = "Profile Saved Successfully"
    message1.configure(text=res)
    unique_registrations = len(set(IDs))
    message.configure(text='Total Registrations till now: ' + str(unique_registrations))

def getImagesAndLabels(path):
    imagePaths = [os.path.join(path, f) for f in os.listdir(path) if f.endswith('.jpg')]
    faces = []
    IDs = []
    for imagePath in imagePaths:
        pilImage = Image.open(imagePath).convert('L')
        imageNp = np.array(pilImage, 'uint8')
        try:
            ID = int(os.path.split(imagePath)[-1].split(".")[1])
        except ValueError:
            continue
        faces.append(imageNp)
        IDs.append(ID)
    return faces, IDs

def TrackImages():
    check_haarcascadefile()
    assure_path_exists("Attendance/")
    assure_path_exists("StudentDetails/")
    for k in tv.get_children():
        tv.delete(k)

    recognizer = cv2.face.LBPHFaceRecognizer_create()
    if os.path.isfile("TrainingImageLabel/Trainner.yml"):
        recognizer.read("TrainingImageLabel/Trainner.yml")
    else:
        mess.showerror(title='Data Missing', message='Please click on Save Profile to reset data!')
        return

    harcascadePath = "haarcascade_frontalface_default.xml"
    faceCascade = cv2.CascadeClassifier(harcascadePath)
    cam = cv2.VideoCapture(0)
    font = cv2.FONT_HERSHEY_SIMPLEX

    while True:
        ret, im = cam.read()
        if not ret:
            break

        gray = cv2.cvtColor(im, cv2.COLOR_BGR2GRAY)
        faces = faceCascade.detectMultiScale(gray, 1.2, 5)

        for (x, y, w, h) in faces:
            cv2.rectangle(im, (x, y), (x + w, y + h), (225, 0, 0), 2)
            Id, conf = recognizer.predict(gray[y:y + h, x:x + w])

            name = fetch_student_name(Id)
            if name:
                cv2.putText(im, name, (x, y - 10), font, 1, (255, 255, 255), 2)

                current_date = datetime.datetime.now().strftime("%Y-%m-%d")
                if not is_attendance_marked(Id, current_date):
                    current_time = datetime.datetime.now().strftime("%H:%M:%S")
                    mark_attendance(Id, name, current_date, current_time)
                    tv.insert('', 'end', text=Id, values=(name, current_date, current_time))
            else:
                cv2.putText(im, "Unknown", (x, y - 10), font, 1, (255, 255, 255), 2)

        cv2.imshow('Taking Attendance', im)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cam.release()
    cv2.destroyAllWindows()
    cv2.waitKey(1)

def fetch_student_name(Id):
    connection = get_db_connection()
    cursor = connection.cursor()
    cursor.execute("SELECT name FROM StudentDetails WHERE student_id = %s", (Id,))
    name = cursor.fetchone()
    cursor.close()
    connection.close()
    return name[0] if name else None

def is_attendance_marked(Id, current_date):
    connection = get_db_connection()
    cursor = connection.cursor()
    cursor.execute("SELECT * FROM Attendance WHERE student_id = %s AND date = %s", (Id, current_date))
    existing_entry = cursor.fetchone()
    cursor.close()
    connection.close()
    return existing_entry is not None

def mark_attendance(Id, name, current_date, current_time):
    connection = get_db_connection()
    cursor = connection.cursor()
    cursor.execute("INSERT INTO Attendance (student_id, name, date, time) VALUES (%s, %s, %s, %s)",
                   (Id, name, current_date, current_time))
    connection.commit()
    cursor.close()
    connection.close()

def display_registration_details():
    display_window = tk.Toplevel(window)
    display_window.title("Registered Details")
    display_window.geometry("600x400")
    display_window.configure(bg="#f0f0f0")

    style = ttk.Style()
    style.configure("Treeview", rowheight=25)

    detail_tree = ttk.Treeview(display_window, columns=('ID', 'Name'), show='headings', style="Treeview")
    detail_tree.heading('ID', text='ID')
    detail_tree.heading('Name', text='Name')
    detail_tree.column('ID', width=100)
    detail_tree.column('Name', width=200)
    detail_tree.pack(expand=True, fill=tk.BOTH, padx=10, pady=10)

    connection = get_db_connection()
    cursor = connection.cursor()
    cursor.execute("SELECT student_id, name FROM StudentDetails")
    student_data = cursor.fetchall()
    cursor.close()
    connection.close()

    for row in student_data:
        detail_tree.insert('', 'end', values=(row[0], row[1]))

    def remove_entry():
        selected_item = detail_tree.selection()
        if not selected_item:
            mess.showerror(title='Selection Error', message='Please select a student to remove.')
            return

        item_values = detail_tree.item(selected_item, 'values')
        if item_values:
            id_to_remove = item_values[0]
            delete_student_details(id_to_remove)
            detail_tree.delete(selected_item)

    def delete_student_details(student_id):
        # Delete images associated with the student
        image_path = f"TrainingImage/"
        for file_name in os.listdir(image_path):
            if file_name.startswith(f"{student_id}."):
                os.remove(os.path.join(image_path, file_name))

        # Delete student details from the database
        connection = get_db_connection()
        cursor = connection.cursor()
        cursor.execute("DELETE FROM StudentDetails WHERE student_id = %s", (student_id,))
        cursor.execute("DELETE FROM Attendance WHERE student_id = %s", (student_id,))
        connection.commit()
        cursor.close()
        connection.close()

    remove_button = tk.Button(display_window, text="Remove Selected", command=remove_entry, fg="Black", bg="White",
                              font=('Helvetica', 14, 'bold'))
    remove_button.pack(pady=10)



def download_attendance():
    start_date = cal_start.get_date()

    connection = get_db_connection()
    cursor = connection.cursor()
    cursor.execute("SELECT student_id, name, date, time FROM Attendance WHERE date = %s", (start_date,))
    attendance_data = cursor.fetchall()
    cursor.close()
    connection.close()

    if not attendance_data:
        mess.showinfo(title='No Data', message='No attendance data available for the selected date.')
        return

    file_path = filedialog.asksaveasfilename(defaultextension=".pdf", filetypes=[("PDF files", "*.pdf")])
    if file_path:
        create_pdf_report(file_path, attendance_data)

def create_pdf_report(file_path, attendance_data):
    doc = SimpleDocTemplate(file_path, pagesize=letter)
    elements = []

    data = [['Student ID', 'Name', 'Date', 'Time']]
    data.extend(attendance_data)

    table = Table(data)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
    ]))

    elements.append(table)
    doc.build(elements)

    mess.showinfo(title='Download Successful', message='Attendance sheet downloaded successfully!')

def download_attendance_by_name():
    name = search_entry.get().strip()
    if not name:
        mess.showerror(title='Input Error', message='Please enter a name to search.')
        return

    connection = get_db_connection()
    cursor = connection.cursor()
    cursor.execute("SELECT student_id, name, date, time FROM Attendance WHERE name = %s", (name,))
    attendance_data = cursor.fetchall()
    cursor.close()
    connection.close()

    if not attendance_data:
        mess.showinfo(title='No Data', message='No attendance data available for the specified name.')
        return

    file_path = filedialog.asksaveasfilename(defaultextension=".pdf", filetypes=[("PDF files", "*.pdf")])
    if file_path:
        create_pdf_report(file_path, attendance_data)

# Create database and tables
create_database()

# Initialize the main window
window = tk.Tk()
window.geometry("1400x900")
window.resizable(True, True)
window.title("Attendance System")
window.configure(background='#f0f0f0')

# Main Frame
main_frame = tk.Frame(window, bg="#f0f0f0")
main_frame.pack(expand=True, fill=tk.BOTH, padx=20, pady=20)

# Header Frame
header_frame = tk.Frame(main_frame, bg="#f0f0f0")
header_frame.pack(fill=tk.X, pady=10)

message3 = tk.Label(header_frame, text="Face Recognition Based Attendance System", fg="black", bg="#f0f0f0",
                   font=('Helvetica', 24, 'bold'))
message3.pack()

# Clock and Date Frame
clock_date_frame = tk.Frame(header_frame, bg="#f0f0f0")
clock_date_frame.pack(fill=tk.X)

frame3 = tk.Frame(clock_date_frame, bg="#c4c6ce")
frame3.pack(side=tk.RIGHT, padx=10)

frame4 = tk.Frame(clock_date_frame, bg="#c4c6ce")
frame4.pack(side=tk.LEFT, padx=10)

ts = time.time()
date = datetime.datetime.fromtimestamp(ts).strftime('%Y-%m-%d')
day, month, year = date.split("-")
mont = {'01': 'January', '02': 'February', '03': 'March', '04': 'April', '05': 'May', '06': 'June',
        '07': 'July', '08': 'August', '09': 'September', '10': 'October', '11': 'November', '12': 'December'}

datef = tk.Label(frame4, text=day + "-" + mont[month] + "-" + year + "  |  ", fg="black", bg="#f0f0f0",
                 font=('Helvetica', 18, 'bold'))
datef.pack(fill='both', expand=1)

clock = tk.Label(frame3, fg="black", bg="#f0f0f0", font=('Helvetica', 18, 'bold'))
clock.pack(fill='both', expand=1)
tick()

# Left and Right Frames
left_frame = tk.Frame(main_frame, bg="#e0e0e0", highlightbackground="black", highlightthickness=1)
left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=10, pady=10)

right_frame = tk.Frame(main_frame, bg="#e0e0e0", highlightbackground="black", highlightthickness=1)
right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=10, pady=10)

# Left Frame Content
head1 = tk.Label(left_frame, text="For Already Registered", fg="black", bg="#3ece48", font=('Helvetica', 14, 'bold'))
head1.pack(fill=tk.X, pady=5)

lbl3 = tk.Label(left_frame, text="Attendance", fg="black", bg="#e0e0e0", font=('Helvetica', 16, 'bold'))
lbl3.pack(pady=10)

tv = ttk.Treeview(left_frame, height=22, columns=('name', 'date', 'time'), style="Treeview")
tv.column('#0', width=82)
tv.column('name', width=130)
tv.column('date', width=133)
tv.column('time', width=133)
tv.pack(expand=True, fill=tk.BOTH, padx=10, pady=10)
tv.heading('#0', text='ID')
tv.heading('name', text='NAME')
tv.heading('date', text='DATE')
tv.heading('time', text='TIME')

style = ttk.Style()
style.configure("Treeview", rowheight=25, font=('Helvetica', 12))
style.configure("Treeview.Heading", font=('Helvetica', 13, 'bold'))

scroll = ttk.Scrollbar(left_frame, orient='vertical', command=tv.yview)
scroll.pack(side=tk.RIGHT, fill=tk.Y)
tv.configure(yscrollcommand=scroll.set)

trackImg = tk.Button(left_frame, text="Take Attendance", command=TrackImages, fg="black", bg="yellow",
                     font=('Helvetica', 14, 'bold'))
trackImg.pack(pady=10)

# Right Frame Content
head2 = tk.Label(right_frame, text="For New Registrations", fg="black", bg="#3ece48", font=('Helvetica', 16, 'bold'))
head2.pack(fill=tk.X, pady=5)

lbl = tk.Label(right_frame, text="Enter ID", fg="black", bg="#e0e0e0", font=('Helvetica', 16, 'bold'))
lbl.pack(pady=5)

txt = tk.Entry(right_frame, fg="white", font=('Helvetica', 14, 'bold'))
txt.pack(pady=5)

lbl2 = tk.Label(right_frame, text="Enter Name", fg="black", bg="#e0e0e0", font=('Helvetica', 16, 'bold'))
lbl2.pack(pady=5)

txt2 = tk.Entry(right_frame, fg="white", font=('Helvetica', 14, 'bold'))
txt2.pack(pady=5)

message1 = tk.Label(right_frame, text="1) Take Images  >>>  2) Save Profile", bg="#e0e0e0", fg="black",
                    font=('Helvetica', 14, 'bold'))
message1.pack(pady=5)

message = tk.Label(right_frame, text="", bg="#e0e0e0", fg="black", font=('Helvetica', 15, 'bold'))
message.pack(pady=5)

takeImg = tk.Button(right_frame, text="Take Images", command=TakeImages, fg="Black", bg="White",
                    font=('Helvetica', 14, 'bold'))
takeImg.pack(pady=5)

trainImg = tk.Button(right_frame, text="Save Profile", command=TrainImages, fg="Black", bg="White",
                     font=('Helvetica', 14, 'bold'))
trainImg.pack(pady=5)

quitWindow = tk.Button(right_frame, text="Quit", command=window.destroy, fg="black", bg="red",
                       font=('Helvetica', 14, 'bold'))
quitWindow.pack(pady=5)

displayButton = tk.Button(right_frame, text="Display Details", command=display_registration_details, fg="black", bg="purple",
                          font=('Helvetica', 14, 'bold'))
displayButton.pack(pady=5)

# Date Picker and Download Button
cal_start = DateEntry(right_frame, width=12, background='White', foreground='Black', borderwidth=2, date_pattern='yyyy-mm-dd')
cal_start.pack(pady=5)

downloadButton = tk.Button(right_frame, text="Download Attendance by Date", command=download_attendance, fg="black", bg="White",
                           font=('Helvetica', 14, 'bold'))
downloadButton.pack(pady=5)

# Search Entry and Button
search_label = tk.Label(right_frame, text="Search by Name", fg="black", bg="#e0e0e0", font=('Helvetica', 16, 'bold'))
search_label.pack(pady=5)

search_entry = tk.Entry(right_frame, fg="White", font=('Helvetica', 14, 'bold'))
search_entry.pack(pady=5)

searchButton = tk.Button(right_frame, text="Download Attendance by Name", command=download_attendance_by_name, fg="black", bg="green",
                         font=('Helvetica', 14, 'bold'))
searchButton.pack(pady=5)

menubar = tk.Menu(window, relief='ridge')
filemenu = tk.Menu(menubar, tearoff=0)
filemenu.add_command(label='Contact Us', command=contact)
filemenu.add_command(label='Exit', command=window.destroy)
menubar.add_cascade(label='Help', font=('Helvetica', 18, 'bold'), menu=filemenu)

window.configure(menu=menubar)

# Bind the on_closing function to the window close event
window.protocol("WM_DELETE_WINDOW", on_closing)

window.mainloop()
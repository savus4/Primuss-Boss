import time
from datetime import datetime
from datetime import time as dtTime
import random
import os
import sys
import json
import logging
import smtplib
import requests
import ssl
import traceback
from selenium.webdriver.chrome.options import Options
from selenium.webdriver import Chrome
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common import exceptions as SEL_EXC

from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

subjects = {"Digitale Signalverarbeitung": "DS",
            "Automotive-Projekt": "VR",
            "Informations- und Medienkompetenz (PLV3)": "PLV3",
            "Praktikum Digitale Signalverarbeitung": "DSP",
            "Sicherheitskritische Systeme": "SKS",
            "Sensoren und Aktoren für Automotive-Anwendungen": "SA"}


def init():
    # Logging config
    log_file = "log.txt"
    if os.path.exists(log_file):
        os.remove(log_file)
    logging.basicConfig(filename=log_file, level=logging.INFO)
    # Get credentials
    credentialsFolder = "./credentials"
    if not os.path.exists(credentialsFolder):
        os.mkdir(credentialsFolder)
    dataFolder = "./data"
    if not os.path.exists(dataFolder):
        os.mkdir(dataFolder)
    primussCredentialsFile = "primussCredentials.json"
    if not os.path.exists(os.path.join(credentialsFolder, primussCredentialsFile)):
        # if data file does not exist, ask for credentials and create one (only first time)
        cred = dict()
        cred["username"] = input(
            "Please enter your primuss username (without \"@thi.de\"): ")
        cred["password"] = input("Please enter your primuss password: ")
        with open(os.path.join(credentialsFolder, primussCredentialsFile), "w") as json_file:
            json.dump(cred, json_file)

    emailCredentialsFile = "emailCredentials.json"
    if not os.path.exists(os.path.join(credentialsFolder, emailCredentialsFile)):
        # if email credential file does not exist, ask for credentials and create one (only first time)
        cred = dict()
        cred["username"] = input(
            "Please enter your Gmail address (the email with your grades will be sent from and to this address): ")
        cred["password"] = input(
            """Please enter your email password (with Gmail you have to create an 
            app password if you have 2-factor authentication enabled): """)
        with open(os.path.join(credentialsFolder, emailCredentialsFile), "w") as json_file:
            json.dump(cred, json_file)

    # get credentials form email credential file
    with open(os.path.join(credentialsFolder, emailCredentialsFile)) as json_file:
        data = json.load(json_file)
        my_email_adress = data["username"]
        my_email_password = data["password"]

    # get credentials form data.json file
    with open(os.path.join(credentialsFolder, primussCredentialsFile)) as json_file:
        data = json.load(json_file)
        primuss_username = data["username"]
        primuss_password = data["password"]

    wait_for_internet_connection(my_email_adress, my_email_password)
    return primuss_username, primuss_password, my_email_adress, my_email_password, dataFolder


def main():
    waitingTime = get_wait_time()

    while True:
        # setup
        primuss_username, primuss_password, my_email_address, my_email_password, dataFolder = init()
        # scrape grades from website
        results = get_grades(primuss_username, primuss_password,
                             my_email_address, my_email_password)
        
        # only act, if grades could be fetched
        if len(results) != 0:
            # put new results into a string
            results_str = get_results_string(results)

            # check if any grades have changed
            results_path = os.path.join(dataFolder, "cachedResults.json")
            changed_results: dict = check_for_changes(results_path, results)
            # save new grades to disk
            with open(results_path, "w") as json_file:
                json.dump(results, json_file)

            # send email, if any grades have changed
            if len(changed_results) != 0:
                subject = get_subject(changed_results)
                print("Email sent: \"" + subject + "\"")
                send_mail(subject, results_str,
                          my_email_address, my_email_password)
            else:
                print("No changes were found.")
        else:
            print("No results were collected. Look at your email inbox for more infos.")
        print("Waiting " + str(waitingTime) + " seconds until next check.")
        time.sleep(waitingTime)

def get_results_string(results):
    results_str = str()
    for key in results:
        results_str += str(key) + ": " + results[key] + "\n\n"
    return results_str

def get_wait_time():
    now_time = datetime.utcnow().time()
    weekday = datetime.utcnow().weekday()
    if now_time >= dtTime(23, 00) or now_time <= dtTime(5, 00) or weekday >= 5:
        wait_time = 30*60
    else:
        wait_time = 5*60
    variance = random.randint(1, 4)
    wait_time += variance*60
    return wait_time


def get_subject_abbreviation(subject):
    for subject_key in subjects:
        if str(subject) == str(subject_key):
            return subjects[subject_key]
    return subject


def get_subject(changed_results):
    subject = str()
    if len(changed_results) == 1:
        for cur_subject in changed_results:
            subject = get_subject_abbreviation(
                cur_subject) + ": " + changed_results[cur_subject]
    else:
        subject = "Changes in: "
        for cur_subject in changed_results:
            subject += get_subject_abbreviation(cur_subject) + ", "
        subject = subject[0:-2]
    return subject


def check_for_changes(resultsPath, currentData):
    changedData = dict()
    if os.path.exists(resultsPath):
        with open(resultsPath) as json_file:
            cachedData = json.load(json_file)
            for subject in currentData:
                for cachedSubject in cachedData:
                    if subject == cachedSubject and currentData[subject] != cachedData[cachedSubject]:
                        changedData[subject] = currentData[subject]
    return changedData


def get_grades(primuss_username, primuss_password, email_address, email_password):
    results = dict()
    # Start browser
    headless = True
    if headless:
        chromeOptions = Options()
        chromeOptions.add_argument("headless")
        browser = Chrome(options=chromeOptions)
        # Random bigger window size, to make buttons clickable
        #browser.set_window_size(1400, 800)
    else:
        browser = Chrome()
    browser.get('https://www3.primuss.de/cgi-bin/login/index.pl?FH=fhin')

    try:
        # Logging in
        username = browser.find_element_by_id("username")
        username.click()
        username.clear()
        username.send_keys(primuss_username)
        password = browser.find_element_by_id("password")
        username.click()
        password.clear()
        password.send_keys(primuss_password)
        button = browser.find_element_by_xpath(
            '/html/body/div/div[5]/form/div[4]/button')
        button.click()

        # Get to grad announcement page
        open_menu = WebDriverWait(browser, 10).until(
            EC.element_to_be_clickable(
                (By.XPATH, '//*[@id="main"]/div[1]/div/div[1]/button'))
        )
        open_menu.click()
        my_exams = WebDriverWait(browser, 10).until(
            EC.element_to_be_clickable(
                (By.XPATH, '//*[@id="nav-prim"]/div/ul/li[4]/a'))
        )
        my_exams.click()
        my_grades = browser.find_element_by_xpath(
            '//*[@id="main"]/div[2]/div[1]/div[2]/form/input[6]')
        my_grades.click()

        # Get the current grades
        element = WebDriverWait(browser, 20).until(
            EC.presence_of_element_located(
                (By.XPATH, '//*[@id="content-body"]/table[2]/tbody[2]'))
        )
        new_grades = element.get_attribute('innerHTML')

        # Parse grades from table
        rows = new_grades.split('<tr')
        i = 0
        tmp = dict()
        for e in rows:
            tmp[i] = e.split('<td')
            i = i + 1

        for key in tmp:
            if len(tmp[key]) == 8:
                new_key = tmp[key][3].split('<')[0][1:]
                new_grade = tmp[key][6]
                results[new_key] = new_grade.split('<b>')[1].split('</b>')[0]
    except:
        exc_type, _, _ = sys.exc_info()
        content = traceback.format_exc()
        print(str(exc_type.__name__) + "\n\n" + content)
        logging.error(content)

        send_mail(str(exc_type.__name__) + " was thrown!",
                  content, email_address, email_password)
    finally:
        browser.close()

    return results


def send_mail(subject, content, email_address, password):

    # set up the SMTP server
    s = smtplib.SMTP_SSL(host='smtp.gmail.com', port=465,
                         context=ssl.create_default_context())
    s.ehlo()
    s.login(email_address, password)

    # create a message
    msg = MIMEMultipart()

    # setup the parameters of the message
    msg['From'] = email_address
    msg['To'] = "Primuss Boss<" + email_address + ">"
    msg['Subject'] = subject

    # add in the message body
    msg.attach(MIMEText(content, 'plain'))

    # send the message via the server set up earlier.
    s.send_message(msg)
    del msg

    # Terminate the SMTP session and close the connection
    s.quit()


def wait_for_internet_connection(email_address, email_password):
    timeout = 5
    bigger_timeout = 100
    wait_time = 100
    counter = 0
    exception_name = str()
    content = str()
    while True:
        try:
            requests.get('https://google.com/', timeout=timeout)
            return
        except:
            time.sleep(timeout)
            counter += timeout
            exc_type, _, _ = sys.exc_info()
            exception_name = exc_type.__name__
            content = traceback.format_exc()
            logging.warning(
                "No internet connection. Trying to reconnect in " + str(timeout) + " seconds.")
            pass
        if counter >= wait_time:
            logging.error("Primuss Boss isn't active since " + str(counter/60) +
                          " minutes because of no internet connection.\n\n" +
                          exception_name + "\n\n" + content)
            timeout = bigger_timeout
            break

if __name__ == '__main__':
    main()

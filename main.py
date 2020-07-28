import time
import os
import json
from selenium.webdriver.chrome.options import Options
from selenium.webdriver import Chrome
import smtplib
import ssl

from string import Template

from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText


def init():
    # Get credentials
    credentialPath = "./primussCredentials.json"
    if not os.path.exists(credentialPath):
        # if data file does not exist, ask for credentials and create one (only first time) 
        cred = dict()
        cred["username"] = input("Please enter your primuss username: ")
        cred["password"] = input("Please enter your primuss password: ")
        with open(credentialPath, "w") as json_file:
            json.dump(cred, json_file)

    emailCredentialPath = "./emailCredentials"
    if not os.path.exists(emailCredentialPath):
        # if email credential file does not exist, ask for credentials and create one (only first time) 
        cred = dict()
        cred["username"] = input("Please enter your email address (the email with your grades will be sent from and to this address): ")
        cred["password"] = input("Please enter your email password (with Gmail you have to create an app password if you have 2-factor authentication enabled): ")
        with open(emailCredentialPath, "w") as json_file:
            json.dump(cred, json_file)

    # get credentials form email credential file
    with open(emailCredentialPath) as json_file:
        data = json.load(json_file)
        my_email_adress = data["username"]
        my_email_password = data["password"]

    # get credentials form data.json file
    with open(credentialPath) as json_file:
        data = json.load(json_file)
        primuss_username = data["username"]
        primuss_password = data["password"]

    return primuss_username, primuss_password, my_email_adress, my_email_password


def main():
    # setup
    primuss_username, primuss_password, my_email_address, my_email_password = init()
    results = get_grades(primuss_username, primuss_password)
    
    # print grades
    results_str = str()
    for key in results:
        results_str += str(key) + ": " + results[key] + "\n\n"
    #print(results_str)

    results_path = "./cachedResults.json"
    changed_results: dict = check_for_changes(results_path, results)
    with open(results_path, "w") as json_file:
            json.dump(results, json_file)

    if len(changed_results) != 0:
        subject = get_subject(changed_results)
        send_mail(subject, results_str, my_email_address, my_email_password)
    

def get_subject(changed_results):
    subject = str()
    if len(changed_results) == 1:
        for cur_subject in changed_results:
            subject = str(cur_subject) + ": " + changed_results[cur_subject]
    else:
        subject = "Changes in: "
        for cur_subject in changed_results:
            subject += str(cur_subject) + ", "
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

def get_grades(primuss_username, primuss_password):
    # Start browser
    headless = False
    if headless:
        chromeOptions = Options()
        chromeOptions.add_argument("--headless")
        browser = Chrome(options=chromeOptions)
    else:
        browser = Chrome()
    browser.get('https://www3.primuss.de/cgi-bin/login/index.pl?FH=fhin')
    
    # Logging in
    username = browser.find_element_by_id("username")
    username.click()
    username.clear()
    username.send_keys(primuss_username)
    password = browser.find_element_by_id("password")
    username.click()
    password.clear()
    password.send_keys(primuss_password)
    button = browser.find_element_by_xpath('/html/body/div/div[5]/form/div[4]/button')
    button.click()

    # Get to grad announcement page
    my_exams = browser.find_element_by_xpath('//*[@id="nav-prim"]/div/ul/li[4]/a')
    my_exams.click()
    my_grades = browser.find_element_by_xpath('//*[@id="main"]/div[2]/div[1]/div[2]/form/input[6]')
    my_grades.click()
    time.sleep(3)

    # Get the current grades
    new_grades = browser.find_element_by_xpath('//*[@id="content-body"]/table[2]/tbody[2]').get_attribute('innerHTML')
    
    browser.close()

    # Parse grades from table
    rows = new_grades.split('<tr')
    i = 0
    tmp = dict()
    for e in rows:
        tmp[i] = e.split('<td')
        i = i + 1

    results = dict()
    for key in tmp:
        if len(tmp[key]) == 8:
            new_key = tmp[key][3].split('<')[0][1:]
            new_grade = tmp[key][6]
            results[new_key] = new_grade.split('<b>')[1].split('</b>')[0]
    return results

def send_mail(subject, content, email_address, password):

    # set up the SMTP server
    context = ssl.create_default_context()
    s = smtplib.SMTP_SSL(host='smtp.gmail.com', port=465, context=context)
    s.ehlo()

    s.login(email_address, password)

    # For each contact, send the email:
    msg = MIMEMultipart() # create a message

    # setup the parameters of the message
    msg['From']=email_address
    msg['To']=email_address
    msg['Subject']=subject
    
    # add in the message body
    msg.attach(MIMEText(content, 'plain'))
    
    # send the message via the server set up earlier.
    s.send_message(msg)
    del msg
        
    # Terminate the SMTP session and close the connection
    s.quit()

if __name__ == '__main__':
    main()
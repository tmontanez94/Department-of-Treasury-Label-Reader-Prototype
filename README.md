# Department of Treasury Label Reader Prototype

Created by Tomas Montanez



## Project Summary

This was a very fun project, as it has been some time since I used my skills in Python and related development tools. Python is one of the languages I am most comfortable with, and I wanted to build this prototype using technology that I could realistically explain, maintain, and run in a government-computer environment. While using a government computer as I am currently in the Marine Corps and still have access to a governemnt computer to display the project. 

My goal was to create the requested prototype while also keeping in mind the limitations of government systems, including restricted software installation, blocked web services, security concerns, and limited access to external AI tools and cloud-based services.

I also drew from my internship experience, where I worked with a platform that used AI to match manufacturer and supplier invoices. That workflow heavily influenced the design of this prototype. Documents were uploaded, the system extracted key information, users reviewed exceptions, and corrections helped improve future performance. I attempted to replicate that same concept within the context of alcohol label review and compliance verification.

The template training feature was inspired directly by my experience near the end of my internship. One of the workflows I observed allowed users to identify areas of a document that were consistently being read incorrectly. Users could effectively "train" the system by correcting extracted information, allowing future documents with the same format to be processed more accurately. While my implementation is much more simplified, I wanted to demonstrate how recurring alcohol label layouts could benefit from a similar approach through Template Training Mode.

This application is more rudimentary than a production system due to time constraints and because this is a standalone take-home prototype. However, it demonstrates the core workflow of batch label intake, automated field extraction, confidence scoring, compliance review, manual correction, template training, approval, and rejection.  Biggest issue due to what was available and I noticed in the email traffic.  Time, the reason I created a queue already uploaded was due to the time it takes for labels to upload.  This way an auditor can work the labels while more are being uploaded. Local OCR was implemented and tested locally. The deployed version uses a lightweight fallback due to memory limits on the free hosting tier. A production version would use an approved OCR service or dedicated worker infrastructure.



### Systems and Technologies Used



#### Python

Python was selected as the primary development language because it is one of the languages I am most comfortable using and allows rapid development of data-processing and automation workflows. Python also provides strong support for OCR, document processing, and AI-related libraries.



#### FastAPI

FastAPI was used as the backend framework because it is lightweight, easy to deploy, and allows API endpoints to be created quickly. It also provides a modern architecture that can easily be expanded into a larger production system.



#### HTML, CSS, and JavaScript

The frontend was intentionally built using standard web technologies. I wanted to avoid relying on specialized frameworks that may not always be available or approved within government environments. These technologies are widely understood, easy to maintain, and provide a straightforward user experience.



#### OCR (Optical Character Recognition)

OCR was used to simulate the automated reading of alcohol labels. While OCR has limitations when dealing with decorative fonts, curved text, and complex label designs, it serves as a reasonable proof-of-concept for extracting information from uploaded labels.



#### Template Training Mode

Template Training Mode was included to address one of OCR's biggest weaknesses: recurring formatting issues. Rather than requiring an agent to repeatedly correct the same label design, the system allows corrections to be saved and reused. This concept was directly inspired by document-processing workflows I observed during my internship.



#### Folder-Based Workflow

The application uses separate folders for uploaded, verified, rejected, and template-based labels. This approach was chosen because it mirrors how many government workflows organize and track documents through different stages of review while remaining simple enough for a prototype environment.



#### Design Philosophy

Throughout the project, I tried to balance automation with human oversight. The objective was not to replace compliance agents, but rather to reduce the amount of time spent performing repetitive verification tasks. By automatically extracting information, identifying low-risk submissions, highlighting missing information, and supporting batch processing, the system allows agents to focus their attention on labels that require deeper review.



This philosophy mirrors many real-world government and industry systems where automation assists human decision-makers rather than replacing them entirely.

## 

## Approach

The prototype is designed around a compliance-agent workflow:

1. Labels enter the **Pending Review Queue**.
2. The system attempts to read the label and populate key fields.
3. Labels with complete information are marked as low risk and ready for agent review.
4. Labels with missing information are flagged for compliance-agent review.
5. The agent can manually correct extracted fields.
6. The agent can save a template for recurring label layouts.
7. The agent can submit labels as reviewed and accurate.
8. Labels that are missing required information can be marked as not in compliance.
9. Completed labels move out of the active queue into the appropriate folder.


## Why Template Mode Was Added

A major limitation of OCR is that real alcohol labels are not formatted like simple forms. Labels can include curved text, decorative fonts, artwork, low contrast, glare, or text placed in unusual locations.

To address that, this prototype includes **Template Training Mode**. If OCR struggles with a recurring label layout, the agent can correct the fields once and save a template. Future labels from the same brand or layout can use the saved template to reduce repeated manual correction.

This is similar to document review workflows I have seen in industry, where AI is supported by human verification and recurring templates.



## Government-System Considerations

I am familiar with the challenges of working on government systems. Not every tool, website, API, or AI service can be used freely on a government computer.

One example that helped shape my thinking is the Defense Travel System. DTS has flaws, but it supports document upload workflows and can connect travel-card charges to vouchers. A similar concept could apply here: label documents could be uploaded, relevant fields could be extracted, and agents could verify or correct the extracted information before final submission.



## Current Features

* Ready-to-use pending review queue
* Batch upload support
* OCR-assisted label reading
* Manual correction workflow
* Template Training Mode
* Confidence and validation scoring
* Low-risk label identification
* Compliance-agent review flagging
* Submit as reviewed and accurate
* Not In Compliance rejection workflow
* Separate folders for uploaded, verified, rejected, unverified, and template files
* Realistic sample alcohol label images
* Human review notice for final compliance determination
  

## Folder Structure

```text
data/
├── Uploaded Labels/
├── Labels Verified/
├── Labels Rejected/
├── Unverified Labels/
└── Templates/
```

### Uploaded Labels

This folder contains labels currently in the active queue.



### Labels Verified

Labels move here after the agent clicks **Submit as reviewed and accurate**.



### Labels Rejected

Labels move here after the agent clicks **Not In Compliance**.



### Unverified Labels

This folder contains additional sample labels that can be uploaded and tested.



### Templates

This folder stores saved template data from Template Training Mode.



## How to Run the Project Locally

Use Python 3.12.



### Step 1: Open the Project Folder

Open the folder named:

```text
Department of Treasury Label Reader Prototype
```

in VS Code.



### Step 2: Open a Terminal

In VS Code, open:

```text
Terminal → New Terminal
```



### Step 3: Create a Virtual Environment

```powershell
py -3.12 -m venv venv
```



### Step 4: Allow PowerShell Activation for This Session

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned
```



### Step 5: Activate the Virtual Environment



```powershell
.\\venv\\Scripts\\Activate.ps1
```

You should see:

```text
(venv)
```



### Step 6: Upgrade pip

```powershell
python -m pip install --upgrade pip
```



### Step 7: Install Requirements

```powershell
python -m pip install -r requirements.txt
```



### Step 8: Start the Application

```powershell
python -m uvicorn app.main:app --reload --port 8001
```



### Step 9: Open the Application

Open this in your browser:

```text
http://127.0.0.1:8001
```



### Step 10: Stop the Application

Return to the terminal and press:

```text
CTRL + C
```


## Deployment Notes

A deployed application can be hosted using Render or a similar service.

Recommended Render settings:

```text
Build Command:
pip install -r requirements.txt
```

```text
Start Command:
uvicorn app.main:app --host 0.0.0.0 --port $PORT
```




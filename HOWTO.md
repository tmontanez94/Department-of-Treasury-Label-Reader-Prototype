Please Download "Unverified Labels" Folder in "data"

How to Test the Workflow
1. Open the application.
2. Review the labels already loaded in the Pending Review Queue.
3. Click a label to view extracted fields and the label image.
4. or low-risk labels, click Submit as reviewed and accurate.
5. For labels missing required information, click Not In Compliance.
6. Use labels from `data/Unverified Labels` to test new uploads.
7. Try correcting fields manually and saving a template.


Known Limitations
OCR accuracy depends heavily on image quality, lighting, label design, and text placement.
Decorative fonts, curved text, artwork, glare, and low contrast can reduce OCR accuracy.
This prototype uses local OCR processing, which can be slower on computers without a GPU.
Template Mode improves recurring label recognition, but it is not a complete replacement for production computer vision.
Some label formatting requirements, such as font size, bold text, placement, and readability, require human review.
Final compliance determinations remain the responsibility of authorized TTB personnel.
This prototype does not integrate directly with COLA or other Treasury systems.
This prototype does not store audit logs at the level required for a production federal system.

Assumptions
This is a standalone proof-of-concept and not a production deployment.
The prototype does not connect directly to COLA.
Sample labels are included to demonstrate the workflow.
A production version would likely require stronger OCR, layout analysis, user authentication, audit logging, and system integration.
Human review remains required for final compliance decisions.

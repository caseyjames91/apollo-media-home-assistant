# AVA text field readability

AVA Bridge 0.9.3 gives all text-entry fields their own dark background,
high-contrast white input text, and brighter hint text.

This fixes text becoming effectively invisible when the same field helper is
used inside Android AlertDialogs, whose default surface can otherwise clash
with the app's dark text-field styling.

import re

_V_D = [[0,1,2,3,4,5,6,7,8,9],[1,2,3,4,0,6,7,8,9,5],[2,3,4,0,1,7,8,9,5,6],
        [3,4,0,1,2,8,9,5,6,7],[4,0,1,2,3,9,5,6,7,8],[5,9,8,7,6,0,4,3,2,1],
        [6,5,9,8,7,1,0,4,3,2],[7,6,5,9,8,2,1,0,4,3],[8,7,6,5,9,3,2,1,0,4],
        [9,8,7,6,5,4,3,2,1,0]]
_V_P = [[0,1,2,3,4,5,6,7,8,9],[1,5,7,6,2,8,3,0,9,4],[5,8,0,3,7,9,6,1,4,2],
        [8,9,1,6,0,4,3,5,2,7],[9,4,5,3,1,2,6,8,7,0],[4,2,8,6,5,7,3,9,0,1],
        [2,7,9,3,8,0,6,4,1,5],[7,0,4,6,9,1,3,2,5,8]]

def _verhoeff_valid(num):
    c = 0
    for i, ch in enumerate(reversed(num)):
        c = _V_D[c][_V_P[i % 8][int(ch)]]
    return c == 0

def validate_phone(phone):
    if not phone:
        return False, "", "Phone khali hai"
    cleaned = re.sub(r"\D", "", phone)
    if len(cleaned) != 10:
        return False, cleaned, f"Phone 10 digit ka hona chahiye (abhi {len(cleaned)} hai)"
    if cleaned[0] not in "6789":
        return False, cleaned, "Indian mobile number 6/7/8/9 se shuru hota hai"
    return True, cleaned, ""

def validate_aadhaar(aadhaar):
    if not aadhaar:
        return False, "", "", "Aadhaar khali hai"
    cleaned = re.sub(r"\D", "", aadhaar)
    if len(cleaned) != 12:
        return False, cleaned, "", f"Aadhaar 12 digit ka hona chahiye (abhi {len(cleaned)} hai)"
    if cleaned[0] in "01":
        return False, cleaned, "", "Aadhaar 2 se shuru hota hai"
    if not _verhoeff_valid(cleaned):
        return False, cleaned, "", "Aadhaar checksum fail - number galat hai"
    return True, cleaned, f"XXXX XXXX {cleaned[-4:]}", ""

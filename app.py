from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)  # Allows WordPress frontend to access this API

@app.route('/assess', methods=['POST'])
def assess_risk():
    data = request.json
    responses = data.get("responses", {})

    # ===== 1. LN Level Evaluation =====
    ln = "LN4"  # Default

    group1_answers = [responses.get(f"group1_q{i}") for i in range(1, 6)]
    if "Yes" in group1_answers:
        ln = "LN1"
    elif "Don't Know" in group1_answers:
        ln = "LN2"

    # Group 3 water source
    if responses.get("group3_q1") in ["Yes", "Don't Know"] and responses.get("group3_q2") == "Potable":
        ln = "LN3" if ln == "LN4" else ln  # Don't downgrade if higher level already

    # Group 7 logic for Nitrite
    if (
        (responses.get("group7_q1") == "Yes" and responses.get("group7_q2") == "Yes") or
        (responses.get("group7_q1") == "Don't Know" and responses.get("group7_q2") in ["Yes", "Don't Know"])
    ):
        ln = "LN3" if ln == "LN4" else ln

    # ===== 2. LA Level Evaluation =====
    la = "LA4"  # Default

    # Group 1 subgroup questions (secondary/tertiary amines)
    subgroup1 = [responses.get(f"group1_subq{i}") for i in range(1, 6)]
    if "Yes" in subgroup1:
        la = "LA1"
    elif "Don't Know" in subgroup1:
        la = "LA2"

    # Group 4
    g4 = responses.get("group4_q1")
    if g4 == "Yes":
        la = "LA1"
    elif g4 == "Don't Know" and la != "LA1":
        la = "LA2"

    # Group 5
    g5 = responses.get("group5_q1")
    if g5 == "Yes" and la not in ["LA1"]:
        la = "LA2"
    elif g5 == "Don't Know" and la not in ["LA1", "LA2"]:
        la = "LA3"

    # Group 6
    g6 = responses.get("group6_q1")
    if g6 == "Yes" and la not in ["LA1"]:
        la = "LA2"
    elif g6 == "Don't Know" and la not in ["LA1", "LA2"]:
        la = "LA3"

    # Group 7 logic for amine
    g7_1 = responses.get("group7_q1")
    g7_2 = responses.get("group7_q2")
    if g7_1 == "Yes" and g7_2 == "Yes" and la not in ["LA1"]:
        la = "LA2"
    elif g7_1 == "Don't Know" and g7_2 in ["Yes", "Don't Know"] and la not in ["LA1", "LA2"]:
        la = "LA3"

    # Group 3 ion exchange water source (amine)
    if responses.get("group3_q1") in ["Yes", "Don't Know"] and responses.get("group3_q2") == "Ion-exchange":
        la = "LA3" if la == "LA4" else la

    # ===== 3. Nitrosamine Risk Evaluation =====
    risk = "nil"

    if ln == "LN1" and la == "LA1" and responses.get("group1_same_step") == "Yes":
        risk = "high"
    elif (ln == "LN1" and la == "LA1") or (ln == "LN1" and la == "LA2") or (ln == "LN2" and la in ["LA1", "LA2"]):
        risk = "moderate"
    elif (ln in ["LN1", "LN2", "LN3"] and la == "LA3") or (la in ["LA1", "LA2", "LA3"] and ln == "LN3"):
        risk = "minor"

    # Chloramine-based minor risk triggers
    if responses.get("group3_q3") == "Yes" or responses.get("group7_q3") == "Yes":
        if risk == "nil":
            risk = "minor"

    # Group 7 logic for nitrosamine risk
    if (
        (g7_1 == "Yes" and g7_2 == "Yes") or
        (g7_1 == "Don't Know" and g7_2 in ["Yes", "Don't Know"])
    ):
        if risk == "nil":
            risk = "minor"
    elif g7_1 == "No" or g7_2 == "No":
        pass  # do not escalate risk

    # ===== 4. Carryover Potential =====
    carry_nitrites = "Yes" if ln in ["LN1", "LN2"] else "No"
    carry_amines = "Yes" if la in ["LA1", "LA2"] else "No"

    # ===== 5. Recommended Actions =====
    actions = []

    if risk == "high":
        actions.append("Nitrosamine Risk (High): Identify potential nitrosamine impurity, evaluate batches for nitrosamines, and establish scientifically sound specifications to ensure no carryover into the drug product.")
    elif risk in ["moderate", "minor"]:
        actions.append(f"Nitrosamine Risk ({risk.title()}): Identify potential nitrosamine impurity, evaluate batches for nitrosamines, and establish scientifically sound specifications to ensure no carryover into the drug product. If specifications are not implemented, monitor batches annually. No out-of-specification results should occur.")
    elif risk == "nil":
        actions.append("Nitrosamine Risk (Nil): No further action required. Document the assessment and perform periodic reassessment.")

    if carry_nitrites == "Yes":
        actions.append("Carryover of Nitrites: Assess the risk of nitrosamine or NDSRI formation in the drug product due to nitrite carryover.")

    if carry_amines == "Yes":
        actions.append("Carryover of Secondary/Tertiary Amines: Assess the risk of nitrosamine or NDSRI formation in the drug product due to amine carryover.")

    if risk == "nil" and carry_nitrites == "No" and carry_amines == "No":
        actions.append("Overall: No immediate action required.")

    return jsonify({
        "ln": ln,
        "la": la,
        "risk": risk,
        "carryNitrites": carry_nitrites,
        "carryAmines": carry_amines,
        "recommendedActions": actions
    })

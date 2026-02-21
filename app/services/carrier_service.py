from app.models.carrier import CarrierVerifyResponse
from app.utils.fmcsa import lookup_fmcsa, normalize_mc


async def verify_carrier(
    mc_number: str, fmcsa_web_key: str
) -> CarrierVerifyResponse:
    carrier = await lookup_fmcsa(mc_number, fmcsa_web_key)
    mc_clean = normalize_mc(mc_number)

    if carrier.status == "NOT_FOUND":
        return CarrierVerifyResponse(
            eligible=False,
            mc_number=mc_clean,
            carrier_name="Unknown",
            reasons=[f"MC number {mc_clean} not found in FMCSA database."],
        )

    reasons: list[str] = []

    # 1. Master flag — are they allowed to operate?
    if carrier.out_of_service:
        reasons.append(
            "Carrier is not allowed to operate"
            f" (OOS since {carrier.oos_date})."
            if carrier.oos_date
            else "Carrier is not allowed to operate."
        )

    # 2. Active authority
    if carrier.authority_status != "A":
        reasons.append(
            f"Authority not active (status: {carrier.authority_status})."
        )

    # 3. Insurance on file >= required (amounts in thousands of USD)
    if carrier.bipd_insurance_on_file < carrier.bipd_required_amount:
        on_file = carrier.bipd_insurance_on_file
        required = carrier.bipd_required_amount
        reasons.append(
            f"Insufficient BIPD insurance: ${on_file}k on file,"
            f" ${required}k required."
        )

    # 4. Registration current
    if carrier.mcs150_outdated:
        reasons.append("MCS-150 registration is outdated.")

    return CarrierVerifyResponse(
        eligible=len(reasons) == 0,
        mc_number=mc_clean,
        carrier_name=carrier.legal_name,
        reasons=reasons,
    )

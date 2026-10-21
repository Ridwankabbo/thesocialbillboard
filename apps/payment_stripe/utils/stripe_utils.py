import stripe
from django.conf import settings

stripe.api_key = settings.STRIPE_SECRET_KEY

# PRICE_LOOKUP = {
#     ("package-1", "monthly"): "price_1RoY9VRfX6BK6Cwps0rAdYAc",
#     ("package-1", "yearly"): "price_1RoYAfRfX6BK6CwpvoVvynJt",
#     ("package-2", "monthly"): "price_1RoYC2RfX6BK6CwpO51ZAqOO",
#     ("package-2", "yearly"): "price_1RoYDARfX6BK6CwpAGo7t0yB",
# }

# clients real payment packages 
# PRICE_LOOKUP = {
#     ("package-1", "monthly"): "price_1RrkFc5izR1x5g2e1F2RTDBG",
#     ("package-1", "yearly"): "price_1RrkH25izR1x5g2ePuDGeeEc",
#     ("package-2", "monthly"): "price_1RrkKF5izR1x5g2eDphYedWD",
#     ("package-2", "yearly"): "price_1RrkLo5izR1x5g2eGfs6QAjB",
# }
# clients test payment packages 
PRICE_LOOKUP = {
    ("package-1", "monthly"): "price_1ThOKe5ItWtJQi02bTMACkWm",
    ("package-1", "yearly"): "price_1ThOLq5ItWtJQi028aQU0c2h",
    ("package-2", "monthly"): "price_1ThON35ItWtJQi02cYCJuUdy",
    ("package-2", "yearly"): "price_1ThOO25ItWtJQi02zSmnzH0e",
}

# PRICE_LOOKUP = {
#     ("package-1", "monthly"): "price_1SaZax7Q7Te59nusdChNPWkR",
#     ("package-1", "yearly"): "price_1SabM07Q7Te59nus79GBw4cn",
#     ("package-2", "monthly"): "price_1TEnlJ7Q7Te59nusQS29qSn6",
#     ("package-2", "yearly"): "price_1TEnmG7Q7Te59nus7OhsNnGy",
# }

# def create_checkout_session(user, package, billing):
#     price_id = PRICE_LOOKUP[(package, billing)]
#     package_number = 1 if package == "package-1" else 2
#     customer = stripe.Customer.create(email=user.email)
#     session = stripe.checkout.Session.create(
#         customer=customer.id,
#         line_items=[{"price": price_id, "quantity": 1}],
#         mode="subscription",
#         success_url="https://thesocialbillboard.com/checkout/success/",
#         cancel_url="https://thesocialbillboard.com/checkout/failed/",
#     )
#     return session.url



def normalize_billing_interval(value):
    if not value:
        return value
    value = value.strip().lower()
    if value in {"month", "monthly"}:
        return "monthly"
    if value in {"year", "yearly"}:
        return "yearly"
    return value


def create_checkout_session(user, package_name, interval):
    from apps.payment_stripe.models import SubscriptionPlan

    normalized_interval = normalize_billing_interval(interval)
    try:
        plan = SubscriptionPlan.objects.get(name=package_name, interval=normalized_interval)
        price_id = plan.stripe_price_id
        success_url = plan.success_url
        cancel_url = plan.cancel_url
    except SubscriptionPlan.DoesNotExist:
        price_id = PRICE_LOOKUP.get((package_name, normalized_interval))
        if not price_id:
            raise ValueError(f"Plan '{package_name}' with interval '{normalized_interval}' not found")
        plan = None
        success_url = None
        cancel_url = None

    # Fallback/default URLs if not set in database
    if not success_url:
        if package_name == "ParentPro" or package_name == "ParentProYearly":
            success_url = "https://thesocialbillboard.com/subscription/status/success/parent"
        elif package_name == "CreatorPro" or package_name == "CreatorProYearly":
            success_url = "https://thesocialbillboard.com/subscription/status/success/creator"
        else:
            success_url = "https://thesocialbillboard.com/subscription/status/success/"

    if not cancel_url:
        if package_name == "ParentPro" or package_name == "ParentProYearly":
            cancel_url = "https://thesocialbillboard.com/subscription/status/failed/parent"
        elif package_name == "CreatorPro" or package_name == "CreatorProYearly":
            cancel_url = "https://thesocialbillboard.com/subscription/status/failed/creator"
        else:
            cancel_url = "https://thesocialbillboard.com/subscription/status/failed/"

    # Get or create Stripe customer
    from apps.payment_stripe.models import Subscription
    sub = Subscription.objects.filter(user=user).first()
    if sub and sub.stripe_customer_id:
        customer_id = sub.stripe_customer_id
    else:
        customers = stripe.Customer.list(email=user.email, limit=1)
        if customers.data:
            customer_id = customers.data[0].id
        else:
            customer = stripe.Customer.create(email=user.email)
            customer_id = customer.id

    # Create Checkout Session
    session = stripe.checkout.Session.create(
        customer=customer_id,
        line_items=[
            {
                "price": price_id,
                "quantity": 1
            }
        ],
        mode="subscription",
        success_url=success_url,
        cancel_url=cancel_url,
    )

    return session.url

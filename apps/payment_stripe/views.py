from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.utils.timezone import make_aware
from django.utils import timezone
from .models import Subscription, SubscriptionPlan
from .utils.stripe_utils import create_checkout_session
import stripe, datetime
from django.conf import settings
from rest_framework import status
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
import stripe, json
from datetime import datetime
from rest_framework.exceptions import NotFound
from django.contrib.auth import get_user_model
User = get_user_model()
# PRICE_LOOKUP = {
#     ("package-1", "monthly"): "price_1RoY9VRfX6BK6Cwps0rAdYAc",
#     ("package-1", "yearly"): "price_1RoYAfRfX6BK6CwpvoVvynJt",
#     ("package-2", "monthly"): "price_1RoYC2RfX6BK6CwpO51ZAqOO",
#     ("package-2", "yearly"): "price_1RoYDARfX6BK6CwpAGo7t0yB",
# }

# client real payment packages
# PRICE_LOOKUP = {
#     ("package-1", "monthly"): "price_1RrkFc5izR1x5g2e1F2RTDBG",
#     ("package-1", "yearly"): "price_1RrkH25izR1x5g2ePuDGeeEc",
#     ("package-2", "monthly"): "price_1RrkKF5izR1x5g2eDphYedWD",
#     ("package-2", "yearly"): "price_1RrkLo5izR1x5g2eGfs6QAjB",
# }
# client test payment packages


PRICE_LOOKUP = {
    ("package-1", "monthly"): "price_1ThOKe5ItWtJQi02bTMACkWm",
    ("package-1", "yearly"): "price_1ThOLq5ItWtJQi028aQU0c2h",
    ("package-2", "monthly"): "price_1ThON35ItWtJQi02cYCJuUdy",
    ("package-2", "yearly"): "price_1ThOO25ItWtJQi02zSmnzH0e",
}


def normalize_billing_interval(value):
    if not value:
        return value
    value = value.strip().lower()
    if value in {"month", "monthly"}:
        return "monthly"
    if value in {"year", "yearly"}:
        return "yearly"
    return value

stripe.api_key = settings.STRIPE_SECRET_KEY


def stripe_value(data, key, default=None):
    try:
        return data[key]
    except (KeyError, TypeError):
        return default


def resolve_subscription_plan(package, billing_interval):
    normalized_billing = normalize_billing_interval(billing_interval)

    plan = SubscriptionPlan.objects.filter(name=package, interval=normalized_billing).first()
    if plan:
        return plan

    plan = SubscriptionPlan.objects.filter(display_name=package, interval=normalized_billing).first()
    if plan:
        return plan

    price_id = PRICE_LOOKUP.get((package, normalized_billing))
    if price_id:
        plan = SubscriptionPlan.objects.filter(stripe_price_id=price_id).first()
        if plan:
            return plan

    plans_for_interval = SubscriptionPlan.objects.filter(interval=normalized_billing)
    if plans_for_interval.count() == 1:
        return plans_for_interval.first()

    return None



class BaseAPIView(APIView):
    def success_response(self, message="Your request Accepted", data=None, status_code= status.HTTP_200_OK):
        return Response(
            {
            "success": True,
            "message": message,
            "status": status_code,
            "data": data or {}
            },
            status=status_code )
    def error_response(self, message="Your request rejected", data=None, status_code= status.HTTP_400_BAD_REQUEST):
        return Response(
            {
            "success": False,
            "message": message,
            "status": status_code,
            "data": data or {}
            },
            status=status_code ) 


#  User payment checkout url give in stripe redirection    
class CreateCheckoutView(BaseAPIView):  # Inherit from BaseAPIView
    permission_classes = [IsAuthenticated]

    def post(self, request):
        package = request.data.get("package_name") or request.data.get("package")
        billing = normalize_billing_interval(request.data.get("interval") or request.data.get("billing"))  # 'monthly' or 'yearly'

        if not package or not billing:
            return self.error_response("Package name and interval are required")

        try:
            session_url = create_checkout_session(request.user, package, billing)
            return self.success_response(
                message="Checkout session created successfully",
                data={"checkout_url": session_url},
                status_code=status.HTTP_200_OK
            )
        except Exception as e:
            return self.error_response(
                message=f"Checkout failed: {str(e)}",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


# user Subscription plan cancellation which only auto renual off and cancel at period end
class CancelSubscriptionView(BaseAPIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            sub = Subscription.objects.get(user=request.user)
        except Subscription.DoesNotExist:
            return self.error_response("No active subscription found for this user.", status_code=404)

        try:
            stripe.Subscription.modify(
                sub.stripe_subscription_id,
                cancel_at_period_end=True
            )
            sub.auto_renew = False
            sub.save()
        except stripe.error.StripeError as e:
            return self.error_response("Stripe error: " + str(e), status_code=400)

        return self.success_response("Subscription cancellation scheduled at period end.", data={"auto_renew": False})




# user Subscription plan upgrade which only monthly subscription can be upgraded yearly
class UpgradeSubscriptionView(BaseAPIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user
        new_package = request.data.get("package_name") or request.data.get("package")
        new_billing = normalize_billing_interval(request.data.get("interval") or request.data.get("billing"))

        if not new_package or not new_billing:
            return self.error_response("Package name and interval are required.", status_code=400)

        try:
            sub = Subscription.objects.get(user=user)
        except Subscription.DoesNotExist:
            return self.error_response("No active subscription found.", status_code=404)

        normalized_current_billing = normalize_billing_interval(sub.billing_interval)

        if normalized_current_billing != "monthly":
            return self.error_response("Only monthly subscriptions can be upgraded.", status_code=400)

        current_package = sub.package

        # Look up price ID dynamically from database
        try:
            plan = SubscriptionPlan.objects.get(name=new_package, interval=new_billing)
            new_price_id = plan.stripe_price_id
        except SubscriptionPlan.DoesNotExist:
            new_price_id = PRICE_LOOKUP.get((new_package, new_billing))

        if not new_price_id:
            return self.error_response("Invalid package or billing option.", status_code=400)

        if new_package == current_package and new_billing == normalized_current_billing:
            return self.error_response("Already subscribed to this package.", status_code=400)

        try:
            stripe_sub = stripe.Subscription.retrieve(sub.stripe_subscription_id)
            item_id = stripe_sub["items"]["data"][0]["id"]

            if stripe_sub.get("cancel_at_period_end"):
                stripe.Subscription.modify(
                    sub.stripe_subscription_id,
                    cancel_at_period_end=False
                )

            stripe.Subscription.modify(
                sub.stripe_subscription_id,
                items=[{
                    "id": item_id,
                    "price": new_price_id
                }],
                proration_behavior="create_prorations",
            )

            sub.package = new_package
            sub.billing_interval = new_billing
            sub.auto_renew = True
            sub.save()

            return self.success_response("Subscription upgraded successfully.")

        except Exception as e:
            return self.error_response(str(e), status_code=500)


# user Subscription status and details
class MySubscriptionView(BaseAPIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            sub = Subscription.objects.get(user=request.user)
        except Subscription.DoesNotExist:
            return self.success_response("No active subscription found for this user.", data={
                "user": {
                    "id": request.user.id,
                    "email": request.user.email,
                    "user_type": request.user.user_type,
                },
                "subscription": None
            })

        # Fetch price from database SubscriptionPlan
        normalized_billing = normalize_billing_interval(sub.billing_interval)
        price_amount = None
        features = []
        user_type = None
        display_name = sub.package

        plan = resolve_subscription_plan(sub.package, normalized_billing)
        if plan:
            price_amount = float(plan.price)
            features = plan.features_list
            user_type = plan.user_type
            display_name = plan.display_name
            plan_name = plan.name
        else:
            # Fallback to Stripe Price Fetch
            price_id = PRICE_LOOKUP.get((sub.package, normalized_billing))
            if price_id:
                try:
                    stripe_price = stripe.Price.retrieve(price_id)
                    price_amount = stripe_price.unit_amount / 100
                except stripe.error.StripeError:
                    pass

        data = {
            "user": {
                "id": request.user.id,
                "email": request.user.email,
                "user_type": request.user.user_type,
            },
            "package": plan_name,
            "plan_display_name": display_name,
            "billing_interval": normalized_billing,
            "price": price_amount,
            "features": features,
            "user_type": user_type,
            "auto_renew": sub.auto_renew,
            "current_period_end": sub.current_period_end,
            "current_period_start": sub.current_period_start,
            "is_current_subscription_valid": (
                sub.current_period_end > timezone.now()
                if sub.current_period_end
                else sub.is_active
            ),
        }

        return self.success_response("Subscription data retrieved successfully.", data)


# Listing of available subscription plans
class SubscriptionPlanListView(BaseAPIView):
    permission_classes = []

    def get(self, request):
        user_type = request.query_params.get("user_type")
        if not user_type and request.user and request.user.is_authenticated:
            user_type = getattr(request.user, "user_type", None)
            
        plans = SubscriptionPlan.objects.all()
        if user_type:
            plans = plans.filter(user_type=user_type)

        data = [
            {
                "id": plan.id,
                "name": plan.name,
                "display_name": plan.display_name,
                "price": float(plan.price),
                "interval": plan.interval,
                "user_type": plan.user_type,
                "features": plan.features_list,
            }
            for plan in plans
        ]
        return self.success_response("Subscription plans retrieved successfully.", data=data)


# All payment and payment history 
class InvoiceHistoryView(BaseAPIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            try:
                # Fetch all Stripe customers associated with the user's email
                customers = stripe.Customer.list(email=request.user.email)
                
                all_invoices = []
                for customer in customers.data:
                    invoices = stripe.Invoice.list(customer=customer.id, limit=100)
                    all_invoices.extend(stripe_value(invoices, "data", []))
                    
                # Sort invoices by created date descending
                all_invoices.sort(key=lambda x: stripe_value(x, "created", 0), reverse=True)

                invoice_data = [
                    {
                        "invoice_id": inv["id"],
                        "number": inv["number"],
                        "amount_paid": inv["amount_paid"] / 100,
                        "created": make_aware(datetime.fromtimestamp(inv["created"])).isoformat(),
                        "status": inv["status"],
                        "invoice_pdf": inv["invoice_pdf"],
                        "description": stripe_value(inv, "description"),
                    }
                    for inv in all_invoices
                ]

                return self.success_response(
                    message="Invoice history retrieved successfully",
                    data={"invoices": invoice_data}
                )

            except stripe.error.StripeError as e:
                return self.error_response(
                    message=f"Stripe API error: {str(e)}",
                    status_code=status.HTTP_400_BAD_REQUEST
                )

        except Exception as e:
            return self.error_response(
                message="An unexpected error occurred",
                data={"error": str(e)},
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

# Card Save Features
# class SaveCardView(BaseAPIView):
#     permission_classes = [IsAuthenticated]

#     def post(self, request):
#         payment_method_id = request.data.get("payment_method_id")
#         if not payment_method_id:
#             return self.error_response("Payment method ID is required", status_code=400)

#         try:
#             sub = Subscription.objects.get(user=request.user)
#             customer_id = sub.stripe_customer_id

#             # Attach to customer
#             stripe.PaymentMethod.attach(
#                 payment_method_id,
#                 customer=customer_id
#             )

#             # Optionally set as default
#             stripe.Customer.modify(
#                 customer_id,
#                 invoice_settings={
#                     'default_payment_method': payment_method_id,
#                 }
#             )

#             return self.success_response("Card saved successfully.")

#         except Exception as e:
#             return self.error_response(str(e), status_code=500)


class ListSavedCardsView(BaseAPIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            sub = Subscription.objects.get(user=request.user)
            customer_id = sub.stripe_customer_id

            cards = stripe.PaymentMethod.list(
                customer=customer_id,
                type="card"
            )

            data = [
                {
                    "id": card.id,
                    "brand": card.card.brand,
                    "last4": card.card.last4,
                    "exp_month": card.card.exp_month,
                    "exp_year": card.card.exp_year,
                    "is_default": (card.id == stripe.Customer.retrieve(customer_id).invoice_settings.default_payment_method)
                }
                for card in cards.data
            ]

            return self.success_response("Saved cards retrieved.", data=data)

        except Exception as e:
            return self.error_response(str(e), status_code=400)



class StripePaymentSuccessView(BaseAPIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        return self.success_response(message="Payment completed successfully.")

# Stripe Webhook to handle events like subscription creation,cancellation,and invoice creation
@csrf_exempt
def stripe_webhook(request):
    print("🔔 Stripe Webhook triggered")

    payload = request.body
    sig_header = request.META.get('HTTP_STRIPE_SIGNATURE')

    if sig_header is None:
        return JsonResponse({'error': 'missing signature header'}, status=400)

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
        )
        print(f" Stripe event received: {event['type']}")
    except stripe.error.SignatureVerificationError:
        return JsonResponse({'error': 'invalid signature'}, status=400)
    except Exception as e:
        print(f" Exception during event parsing: {e}")
        return JsonResponse({'error': str(e)}, status=400)

    if event['type'] == 'checkout.session.completed':
        session = event['data']['object']

        customer_id = stripe_value(session, "customer")
        subscription_id = stripe_value(session, "subscription")
        email = stripe_value(session, "customer_email") or stripe_value(stripe_value(session, "customer_details", {}), "email")

        if not subscription_id:
            return JsonResponse({"error": "No subscription found in session"}, status=400)

        if not email:
            return JsonResponse({"error": "No customer email found in session"}, status=400)

        user = User.objects.filter(email=email).first()
        if not user:
            return JsonResponse({"error": f"No user found with email {email}"}, status=404)

        print(f" Matched user: {user.email}")

        try:
            stripe_sub = stripe.Subscription.retrieve(subscription_id)
            print(" Stripe Subscription:", stripe_sub)

            item_data = stripe_value(stripe_value(stripe_sub, "items", {}), "data", [])
            if item_data:
                item = item_data[0]  # First subscription item
                period_start_ts = stripe_value(item, "current_period_start")  # Access from item, not stripe_sub
                period_end_ts = stripe_value(item, "current_period_end")
                price = stripe_value(item, "price", {})
                price_id = stripe_value(price, "id")
                recurring = stripe_value(price, "recurring", {})
                interval = stripe_value(recurring, "interval")
                print("Interval:", interval)
                package = get_package_from_price_id(price_id)
            else:
                item = {}
                package = "unknown"
                interval = None
                period_start_ts = period_end_ts = None

            Subscription.objects.update_or_create(
                user=user,
                defaults={
                    "stripe_customer_id": customer_id,
                    "stripe_subscription_id": subscription_id,
                    "package": package,
                    "billing_interval": interval,
                    "current_period_start": make_aware(datetime.fromtimestamp(period_start_ts)) if period_start_ts else None,
                    "current_period_end": make_aware(datetime.fromtimestamp(period_end_ts)) if period_end_ts else None,
                    "auto_renew": not stripe_value(stripe_sub, "cancel_at_period_end", False),
                    "is_active": True
                }
            )
            print(" Subscription updated/created")

        except Exception as e:
            return JsonResponse({"error": str(e)}, status=400)

    elif event["type"] == "customer.subscription.deleted":
        print(" Handling customer.subscription.deleted")
        stripe_sub = event["data"]["object"]
        sub = Subscription.objects.filter(stripe_subscription_id=stripe_sub["id"]).first()
        if sub:
            sub.is_active = False
            sub.save()
            print(f" Subscription {sub.id} marked inactive")

    elif event["type"] == "invoice.created":
        invoice = event["data"]["object"]
        print(f"🧾 Invoice created: {invoice['id']}")
        return JsonResponse({'status': 'invoice.created received'}, status=200)

    return JsonResponse({"status": "ok"})

# 🔍 Debugging for package ID resolution
def get_package_from_price_id(price_id):
    print(f" Looking up package for price_id: {price_id}")
    plan = SubscriptionPlan.objects.filter(stripe_price_id=price_id).first()
    if plan:
        print(f"✅ Matched package from DB: {plan.name}")
        return plan.name

    for (pkg, billing), pid in PRICE_LOOKUP.items():
        if pid == price_id:
            print(f"✅ Matched package from fallback: {pkg} with billing {billing}")
            return pkg
    print(" No package match found")
    return "unknown"







# permission classes 
from rest_framework.permissions import BasePermission
class HasPackage1Subscription(BasePermission):
    def has_permission(self, request, view):
        try:
            sub = Subscription.objects.get(user=request.user)
            return (
                sub.package == "package-1" and
                sub.is_active
            )
        except Subscription.DoesNotExist:
            return False
from rest_framework.exceptions import APIException

class SubscriptionRequired(APIException):
    status_code=402
    default_detail = {
        "error_code": "PACKAGE_2_REQUIRED",
        "message": "Upgrade to Package 2 to use this feature."
    }
   
class HasPackage2Subscription(BasePermission):
    def has_permission(self, request, view):
        try:
            sub = Subscription.objects.get(user=request.user)
            print(sub)
            return (
                sub.package == "CreatorPro" and
                sub.is_active
            )
        except Subscription.DoesNotExist:
            pass
        raise SubscriptionRequired(
            detail={
                "error_code": "PACKAGE_2_REQUIRED",
                "message": "Upgrade to subscription pro to use this feature.",
            }
        )
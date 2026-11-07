import re

from django import forms
from django.contrib.auth import get_user_model

from .models import CATEGORIES, COLORWAYS, PATTERNS, SIZES, TYPES, Product

User = get_user_model()

INDIAN_STATES = [
    "Andhra Pradesh", "Assam", "Bihar", "Chhattisgarh", "Delhi", "Goa", "Gujarat", "Haryana", "Himachal Pradesh",
    "Jharkhand", "Karnataka", "Kerala", "Madhya Pradesh", "Maharashtra", "Odisha", "Punjab", "Rajasthan",
    "Tamil Nadu", "Telangana", "Uttar Pradesh", "Uttarakhand", "West Bengal", "Other",
]


class RegisterForm(forms.Form):
    name = forms.CharField(max_length=80, label="Full name")
    email = forms.EmailField()
    phone = forms.CharField(max_length=10, label="Mobile number")
    password = forms.CharField(min_length=6, widget=forms.PasswordInput, help_text="At least 6 characters")
    confirm = forms.CharField(widget=forms.PasswordInput, label="Confirm password")

    def clean_email(self):
        e = self.cleaned_data["email"].strip().lower()
        if User.objects.filter(email__iexact=e).exists() or User.objects.filter(username__iexact=e).exists():
            raise forms.ValidationError("An account with this e-mail already exists")
        return e

    def clean_phone(self):
        p = re.sub(r"\s+", "", self.cleaned_data["phone"])
        if not re.fullmatch(r"[6-9]\d{9}", p):
            raise forms.ValidationError("Enter a valid 10-digit Indian mobile number")
        return p

    def clean(self):
        d = super().clean()
        if d.get("password") and d.get("password") != d.get("confirm"):
            self.add_error("confirm", "Passwords do not match")
        return d

    def save(self):
        d = self.cleaned_data
        first, _, last = d["name"].strip().partition(" ")
        return User.objects.create_user(username=d["email"], email=d["email"], password=d["password"],
                                        first_name=first, last_name=last, phone=d["phone"])


class AddressForm(forms.Form):
    name = forms.CharField(max_length=100, label="Full name")
    phone = forms.CharField(max_length=10, label="Mobile number")
    line = forms.CharField(max_length=255, label="Address (house, street, area)")
    city = forms.CharField(max_length=80)
    state = forms.ChoiceField(choices=[(s, s) for s in INDIAN_STATES])
    pin = forms.CharField(max_length=6, label="PIN code")

    def clean_phone(self):
        p = re.sub(r"\s+", "", self.cleaned_data["phone"])
        if not re.fullmatch(r"[6-9]\d{9}", p):
            raise forms.ValidationError("Enter a valid 10-digit mobile number")
        return p

    def clean_pin(self):
        p = self.cleaned_data["pin"].strip()
        if not re.fullmatch(r"[1-9]\d{5}", p):
            raise forms.ValidationError("Enter a valid 6-digit PIN code")
        return p

    def clean_line(self):
        v = self.cleaned_data["line"].strip()
        if len(v) < 5:
            raise forms.ValidationError("Please enter your full address")
        return v


class ProductForm(forms.ModelForm):
    colorways = forms.MultipleChoiceField(
        choices=[(n, n) for n in COLORWAYS], widget=forms.CheckboxSelectMultiple, label="Colours", required=True,
        error_messages={"required": "Pick at least one colour"},
    )

    class Meta:
        model = Product
        fields = ["name", "category", "type", "price", "mrp", "pattern", "description", "specs", "image", "featured", "is_new"]
        widgets = {"description": forms.Textarea(attrs={"rows": 3}), "specs": forms.Textarea(attrs={"rows": 4})}

    def clean(self):
        d = super().clean()
        if d.get("price") and (d.get("mrp") is None or d["mrp"] < d["price"]):
            d["mrp"] = d["price"]
        return d

    def clean_image(self):
        img = self.cleaned_data.get("image")
        if img and hasattr(img, "size") and img.size > 3 * 1024 * 1024:
            raise forms.ValidationError("Image is larger than 3 MB")
        return img

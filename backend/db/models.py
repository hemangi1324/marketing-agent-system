"""
db/models.py
------------
Pydantic models for all database tables.

Two uses:
1. Request validation — FastAPI uses these to validate what the
   user sends to the API. If a required field is missing, FastAPI
   returns a clear error before anything reaches the database.

2. Response serialisation — FastAPI uses these to shape what gets
   sent back to the frontend.

What is Pydantic?
  A Python library that validates data types. If you say a field
  is an int and the user sends a string, Pydantic rejects it
  automatically with a clear error message. No manual checking needed.
"""

from pydantic import BaseModel, Field, validator
from typing import Optional, List
from datetime import datetime


# ════════════════════════════════════════════════════════════════
# ONBOARDING MODELS
# These are what the user fills in through the UI forms.
# Every field here comes from user input — nothing is pre-filled.
# ════════════════════════════════════════════════════════════════

class CompanyCreateRequest(BaseModel):
    """
    Step 1 of onboarding: Company profile form.
    User fills all of these themselves.
    """
    name:           str = Field(..., min_length=2, max_length=100,
                                description="Your company name")
    industry:       str = Field(..., description="e.g. beauty_ecommerce, fashion, fmcg")
    website:        Optional[str] = Field(None, description="Your website URL")
    brand_voice:    str = Field(..., min_length=20,
                                description="Describe how your brand speaks. Be specific. e.g. 'We are bold, youthful, and aspirational. We use short punchy sentences. We speak directly to the customer using YOU.'")
    avoid_topics:   str = Field(...,
                                description="Comma-separated topics to never mention. e.g. 'competitors, politics, body shaming'")
    primary_color:  str = Field("#000000", description="Your brand's primary hex color")
    country:        str = Field("India", description="Primary market country")

class CompanyUpdateRequest(BaseModel):
    name:           Optional[str] = None
    industry:       Optional[str] = None
    website:        Optional[str] = None
    brand_voice:    Optional[str] = None
    avoid_topics:   Optional[str] = None
    primary_color:  Optional[str] = None

class CompanyResponse(BaseModel):
    id:             int
    name:           str
    industry:       str
    website:        Optional[str]
    brand_voice:    str
    avoid_topics:   str
    primary_color:  str
    country:        str
    created_at:     datetime


class BrandProfileCreateRequest(BaseModel):
    """
    Step 2 of onboarding: Brand voice details.
    More granular than brand_voice in CompanyCreate.
    """
    company_id:         int
    brand_name:         str = Field(..., description="Your brand name as it appears in copy")
    tone_of_voice:      str = Field(..., min_length=10,
                                    description="How your brand writes. e.g. 'Warm, aspirational, inclusive. Celebratory for launches. Urgent for sales. Never cold or clinical.'")
    power_words:        str = Field(...,
                                    description="Words that work for your brand. Comma-separated. e.g. 'glow, luxe, bestseller, limited edition, cult favourite'")
    avoid_phrases:      str = Field(...,
                                    description="Phrases to never use. e.g. 'guaranteed results, best in market, cheapest, skin whitening'")
    preferred_channels: str = Field(...,
                                    description="Comma-separated channels. e.g. 'email,instagram,whatsapp'")
    competitors_avoid:  str = Field("",
                                    description="Competitor names to never mention. e.g. 'Purplle, Mamaearth, MyGlamm'")

class BrandProfileResponse(BaseModel):
    id:                 int
    company_id:         int
    brand_name:         str
    tone_of_voice:      str
    power_words:        str
    avoid_phrases:      str
    preferred_channels: str
    competitors_avoid:  str
    created_at:         datetime


class AudienceSegmentCreateRequest(BaseModel):
    """
    Step 3 of onboarding: Define a target audience.
    User can create multiple segments.
    """
    company_id:         int
    segment_name:       str = Field(..., description="A name for this audience. e.g. 'Young beauty enthusiasts 20-28'")
    age_range:          str = Field(..., description="e.g. '20-30'")
    gender:             str = Field("all", description="'female', 'male', or 'all'")
    location_tier:      str = Field(..., description="e.g. 'Tier 1', 'Tier 1 and Tier 2', 'All India'")
    interests:          str = Field(..., min_length=10,
                                    description="What they care about. e.g. 'skincare routines, K-beauty, makeup tutorials, dermatologist tips'")
    buying_behaviour:   str = Field(..., min_length=10,
                                    description="How they buy. e.g. 'Impulse buyer triggered by influencer content. High cart abandonment. Responds to social proof.'")
    platform_preference:str = Field(...,
                                    description="Where they spend time. e.g. 'instagram,youtube'")

class AudienceSegmentResponse(BaseModel):
    id:                 int
    company_id:         int
    segment_name:       str
    age_range:          str
    gender:             str
    location_tier:      str
    interests:          str
    buying_behaviour:   str
    platform_preference:str
    created_at:         datetime


# ════════════════════════════════════════════════════════════════
# CAMPAIGN MODELS
# ════════════════════════════════════════════════════════════════

class CampaignCreateRequest(BaseModel):
    """
    Human creates a campaign from the UI.
    """
    company_id:             int
    brand_profile_id:       int
    audience_segment_id:    int
    name:                   str = Field(..., min_length=3, description="Campaign name. e.g. 'Diwali Glow Sale 2024'")
    channel:                str = Field(..., description="'email', 'instagram', 'linkedin', 'whatsapp', or 'multi'")
    budget_inr:             int = Field(0, ge=0, description="Campaign budget in INR")
    original_subject_line:  Optional[str] = Field(None, description="The subject line / caption that went live and is failing")
    original_send_time:     Optional[str] = Field(None, description="When was it sent? e.g. 'Monday 09:00 IST'")
    why_failing:            Optional[str] = Field(None, description="Do you know why it's failing? Leave blank if unsure.")

class CampaignMetricsUpdate(BaseModel):
    """User enters current performance numbers."""
    ctr:            float = Field(..., ge=0, description="Current click-through rate %")
    open_rate:      float = Field(0, ge=0, description="Email open rate %")
    roas:           float = Field(0, ge=0, description="Return on ad spend")
    industry_avg_ctr: float = Field(2.1, ge=0, description="Industry benchmark CTR for your category")

class CampaignResponse(BaseModel):
    id:                     int
    company_id:             int
    name:                   str
    channel:                str
    campaign_type:          str
    triggered_by:           str
    manual_prompt:          Optional[str]
    ctr:                    float
    open_rate:              float
    roas:                   float
    industry_avg_ctr:       float
    status:                 str
    heal_attempts:          int
    festival_tag:           Optional[str]           # NEW
    created_at:             datetime
    updated_at:             datetime


class CampaignOfferCreateRequest(BaseModel):
    """
    Financial rules for a campaign.
    Set by human — agents read-only.

    Tip: If you want to lock the discount (not let AI choose),
    set min_discount_pct = max_discount_pct = your fixed value.
    """
    campaign_id:            int
    min_discount_pct:       int = Field(..., ge=0, le=100,
                                        description="Minimum discount %. Set equal to max to lock it.")
    max_discount_pct:       int = Field(..., ge=0, le=100,
                                        description="Maximum discount %. AI will pick within this range.")
    promo_code:             str = Field("", description="Promo code to use in all content. e.g. 'PINK60'")
    offer_end_datetime:     Optional[str] = Field(None, description="Offer deadline. e.g. '2024-11-30 23:59:00'")
    eligible_categories:    str = Field("", description="What products are on sale. e.g. 'skincare, lipsticks, haircare'")
    excluded_items:         str = Field("", description="What is NOT included. e.g. 'luxury brands, new launches'")
    free_shipping:          bool = Field(False, description="Include free shipping in messaging?")
    min_order_value_inr:    int = Field(0, ge=0, description="Minimum order value for the offer")
    approved_by:            str = Field(..., min_length=2, description="Your name — confirms you approve these financial rules")

    @validator("max_discount_pct")
    def max_must_be_gte_min(cls, v, values):
        if "min_discount_pct" in values and v < values["min_discount_pct"]:
            raise ValueError("max_discount_pct must be >= min_discount_pct")
        return v


# ════════════════════════════════════════════════════════════════
# TRIGGER MODELS
# ════════════════════════════════════════════════════════════════

class TriggerRequest(BaseModel):
    """Demo button — simulate a campaign failure."""
    campaign_id:    int
    simulate_ctr:   float = Field(0.3, ge=0, le=100,
                                  description="What CTR to simulate. Default 0.3% = obviously failing.")

class PromptRequest(BaseModel):
    """User types a free-text prompt to create a new campaign."""
    company_id:     int = Field(1)
    user_prompt:    str = Field(..., min_length=10,
                                description="Describe the campaign you want. e.g. 'Launch our new SPF 50 sunscreen targeting working professionals in Tier 1 cities'")

class PromptResponse(BaseModel):
    campaign_id:    int
    prompt_id:      int
    status:         str
    message:        str


# ════════════════════════════════════════════════════════════════
# APPROVAL MODELS
# ════════════════════════════════════════════════════════════════

class ApprovalRequest(BaseModel):
    decided_by:     str = Field(..., min_length=2, description="Your name")
    edited_content: Optional[dict] = Field(None,
                                           description="If you edited any content, pass the changed fields here")

class RejectionRequest(BaseModel):
    decided_by:         str = Field(..., min_length=2)
    rejection_reason:   str = Field("", description="Why are you rejecting? This helps agents generate better content.")


# ════════════════════════════════════════════════════════════════
# GENERATED CONTENT RESPONSE
# ════════════════════════════════════════════════════════════════

class GeneratedAssetsResponse(BaseModel):
    id:                         int
    campaign_id:                int
    attempt_number:             int
    email_subject:              Optional[str]
    email_preheader:            Optional[str]
    email_body:                 Optional[str]
    email_cta:                  Optional[str]
    email_subject_variants:     Optional[List[str]]
    instagram_caption:          Optional[str]
    instagram_hashtags:         List[str]
    instagram_visual_direction: Optional[str]
    linkedin_headline:          Optional[str]
    linkedin_body:              Optional[str]
    linkedin_cta:               Optional[str]
    twitter_post:               Optional[str]
    telegram_message:           Optional[str]      # NEW
    whatsapp_message:           Optional[str]
    send_time_recommendation:   Optional[str]
    chosen_discount_pct:        int
    agent_reasoning:            Optional[str]
    image_url:                  Optional[str]
    image_prompt:               Optional[str]
    image_model:                Optional[str]
    created_at:                 datetime

class RiskAssessmentResponse(BaseModel):
    id:                             int
    brand_safety_score:             int
    brand_safety_note:              str
    legal_risk_score:               int
    legal_risk_note:                str
    cultural_sensitivity_score:     int
    cultural_sensitivity_note:      str
    overall_recommendation:         str
    green_light:                    bool
    decision_reason:                str

class ReasoningLogEntry(BaseModel):
    id:                 int
    agent_name:         str
    reasoning_summary:  str
    status:             str
    cost_usd:           float
    model_used:         str
    duration_ms:        int
    created_at:         datetime

class CostSummary(BaseModel):
    api_calls:          int
    total_tokens:       int
    total_cost_usd:     float
    total_cost_inr:     float

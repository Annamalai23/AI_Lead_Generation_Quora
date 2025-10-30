import streamlit as st
import requests
from agno.agent import Agent
from agno.models.google import Gemini
from firecrawl import FirecrawlApp
from pydantic import BaseModel, Field
from typing import List
import json
from io import StringIO
import csv
import google.generativeai as genai


class QuoraUserInteractionSchema(BaseModel):
    username: str = Field(description="The username of the user who posted the question or answer")
    bio: str = Field(description="The bio or description of the user")
    post_type: str = Field(description="The type of post, either 'question' or 'answer'")
    timestamp: str = Field(description="When the question or answer was posted")
    upvotes: int = Field(default=0, description="Number of upvotes received")
    links: List[str] = Field(default_factory=list, description="Any links included in the post")

class QuoraPageSchema(BaseModel):
    interactions: List[QuoraUserInteractionSchema] = Field(description="List of all user interactions (questions and answers) on the page")

def search_for_urls(company_description: str, firecrawl_api_key: str, num_links: int) -> List[str]:
    url = "https://api.firecrawl.dev/v1/search"
    headers = {
        "Authorization": f"Bearer {firecrawl_api_key}",
        "Content-Type": "application/json"
    }
    query1 = f"quora websites where people are looking for {company_description} services"
    payload = {
        "query": query1,
        "limit": num_links,
        "lang": "en",
        "location": "United States",
        "timeout": 60000,
    }
    response = requests.post(url, json=payload, headers=headers)
    if response.status_code == 200:
        data = response.json()
        if data.get("success"):
            results = data.get("data", [])
            return [result["url"] for result in results]
    return []

def extract_user_info_from_urls(urls: List[str], firecrawl_api_key: str) -> List[dict]:
    user_info_list = []
    firecrawl_app = FirecrawlApp(api_key=firecrawl_api_key)
    
    try:
        for url in urls:
            response = firecrawl_app.extract(
                [url],
                {
                    'prompt': 'Extract all user information including username, bio, post type (question/answer), timestamp, upvotes, and any links from Quora posts. Focus on identifying potential leads who are asking questions or providing answers related to the topic.',
                    'schema': QuoraPageSchema.model_json_schema(),
                }
            )
            
            if response.get('success') and response.get('status') == 'completed':
                interactions = response.get('data', {}).get('interactions', [])
                if interactions:
                    user_info_list.append({
                        "website_url": url,
                        "user_info": interactions
                    })
    except Exception:
        pass
    
    return user_info_list

def format_user_info_to_flattened_json(user_info_list: List[dict]) -> List[dict]:
    flattened_data = []
    
    for info in user_info_list:
        website_url = info["website_url"]
        user_info = info["user_info"]
        
        for interaction in user_info:
            flattened_interaction = {
                "Website URL": website_url,
                "Username": interaction.get("username", ""),
                "Bio": interaction.get("bio", ""),
                "Post Type": interaction.get("post_type", ""),
                "Timestamp": interaction.get("timestamp", ""),
                "Upvotes": interaction.get("upvotes", 0),
                "Links": ", ".join(interaction.get("links", [])),
            }
            flattened_data.append(flattened_interaction)
    
    return flattened_data


def create_prompt_transformation_agent(gemini_api_key: str, model_id: str) -> Agent:
    return Agent(
        model=Gemini(id=model_id, api_key=gemini_api_key)
    )

def prompt_transformation_instructions() -> str:
    return (
        "You are an expert at transforming detailed user queries into concise company descriptions.\n"
        "Your task is to extract the core business/product focus in 3-4 words.\n\n"
        "Examples:\n"
        "Input: \"Generate leads looking for AI-powered customer support chatbots for e-commerce stores.\"\n"
        "Output: \"AI customer support chatbots for e commerce\"\n\n"
        "Input: \"Find people interested in voice cloning technology for creating audiobooks and podcasts\"\n"
        "Output: \"voice cloning technology\"\n\n"
        "Input: \"Looking for users who need automated video editing software with AI capabilities\"\n"
        "Output: \"AI video editing software\"\n\n"
        "Input: \"Need to find businesses interested in implementing machine learning solutions for fraud detection\"\n"
        "Output: \"ML fraud detection\"\n\n"
        "Always focus on the core product/service and keep it concise but clear."
    )

def list_available_gemini_models(api_key: str) -> List[str]:
    try:
        genai.configure(api_key=api_key)
        models = genai.list_models()
        names = []
        for m in models:
            methods = getattr(m, "supported_generation_methods", []) or []
            if "generateContent" in methods or "createContent" in methods:
                name = getattr(m, "name", "")
                if name:
                    names.append(name.split("/")[-1])
        return names
    except Exception:
        return []

def choose_gemini_model(api_key: str, choice: str) -> str:
    if choice != "Auto (recommended)":
        return choice
    available = list_available_gemini_models(api_key)
    priority = [
        "gemini-2.5-flash",
        "gemini-2.5-pro",
        "gemini-2.0-flash",
        "gemini-2.0-pro",
        "gemini-1.5-pro",
        "gemini-1.5-flash",
    ]
    for pid in priority:
        if any(pid in a for a in available):
            return next(a for a in available if pid in a)
    return "gemini-1.5-pro"

def main():
    st.title("🎯 AI Lead Generation Agent (Quora)")
    st.info("This Firecrawl-powered agent helps you generate leads from Quora by searching for relevant posts and extracting user information.")

    with st.sidebar:
        st.header("API Keys")
        firecrawl_api_key = st.text_input("Firecrawl API Key", type="password")
        st.caption(" Get your Firecrawl API key from [Firecrawl's website](https://www.firecrawl.dev/app/api-keys)")
        gemini_api_key = st.text_input("Gemini API Key", type="password")
        st.caption(" Get your Gemini API key from [Google AI Studio](https://aistudio.google.com/app/apikey)")
        gemini_model_id = st.selectbox("Gemini Model", ["Auto (recommended)", "gemini-1.5-pro", "gemini-1.5-flash"], index=0)
        output_csv_path = st.text_input("Output CSV filename", value="leads.csv")
        
        num_links = st.number_input("Number of links to search", min_value=1, max_value=10, value=3)
        
        if st.button("Reset"):
            st.session_state.clear()
            st.rerun()

    user_query = st.text_area(
        "Describe what kind of leads you're looking for:",
        placeholder="e.g., Looking for users who need automated video editing software with AI capabilities",
        help="Be specific about the product/service and target audience. The AI will convert this into a focused search query."
    )

    if st.button("Generate Leads"):
        if not all([firecrawl_api_key, gemini_api_key, user_query]):
            st.error("Please fill in the required API keys and describe what leads you're looking for.")
        else:
            resolved_model = choose_gemini_model(gemini_api_key, gemini_model_id)
            st.caption(f"Using Gemini model: {resolved_model}")

            with st.spinner("Processing your query..."):
                transform_agent = create_prompt_transformation_agent(gemini_api_key, resolved_model)
                instructions = prompt_transformation_instructions()
                prompt = (
                    f"{instructions}\n\n"
                    f"Input: \"{user_query}\"\n"
                    f"Output:"
                )
                company_description = transform_agent.run(prompt)
                company_text = company_description.content if hasattr(company_description, "content") else str(company_description)
                st.write("🎯 Searching for:", company_text)
            
            with st.spinner("Searching for relevant URLs..."):
                urls = search_for_urls(company_text, firecrawl_api_key, num_links)
            
            if urls:
                st.subheader("Quora Links Used:")
                for url in urls:
                    st.write(url)
                
                with st.spinner("Extracting user info from URLs..."):
                    user_info_list = extract_user_info_from_urls(urls, firecrawl_api_key)
                
                with st.spinner("Formatting user info..."):
                    flattened_data = format_user_info_to_flattened_json(user_info_list)

                if flattened_data:
                    st.subheader("Preview Leads")
                    st.dataframe(flattened_data, use_container_width=True)

                    # CSV download
                    csv_buffer = StringIO()
                    if len(flattened_data) > 0:
                        writer = csv.DictWriter(csv_buffer, fieldnames=list(flattened_data[0].keys()))
                        writer.writeheader()
                        writer.writerows(flattened_data)
                    st.download_button(
                        label="Download CSV",
                        data=csv_buffer.getvalue(),
                        file_name="leads.csv",
                        mime="text/csv",
                    )

                    # JSON download
                    st.download_button(
                        label="Download JSON",
                        data=json.dumps(flattened_data, indent=2),
                        file_name="leads.json",
                        mime="application/json",
                    )

                    # Save CSV to disk
                    try:
                        with open(output_csv_path, "w", newline="", encoding="utf-8") as f:
                            file_writer = csv.DictWriter(f, fieldnames=list(flattened_data[0].keys()))
                            file_writer.writeheader()
                            file_writer.writerows(flattened_data)
                        st.success(f"Saved CSV to {output_csv_path}")
                    except Exception as e:
                        st.error(f"Failed to save CSV: {e}")
            else:
                st.warning("No relevant URLs found.")

def _about_footer():
    st.caption("Built with Streamlit, Firecrawl, and Gemini.")

if __name__ == "__main__":
    main()
    _about_footer()

import os
import pandas as pd
from pathlib import Path
from typing import Any, List
from dataclasses import dataclass
from pydantic_ai import Agent, RunContext
from pydantic_ai.models.google import GoogleModel
from pydantic_ai.providers.google import GoogleProvider
from dotenv import load_dotenv

# Load environment variables
BASE_DIR = Path(__file__).resolve().parent
ENV_PATH = BASE_DIR.parent / ".env"
load_dotenv(ENV_PATH)


# Define dependencies structure
@dataclass
class JobMatchingDeps:
    jobs_df: pd.DataFrame


# Set up the Google provider and model according to documentation
provider = GoogleProvider(api_key=os.getenv("GOOGLE_API_KEY"))
model = GoogleModel("gemini-1.5-flash", provider=provider)

# Create our PydanticAI agent with tools
agent = Agent(
    model=model,
    deps_type=JobMatchingDeps,  # Use the dataclass for dependencies
    system_prompt="""You are an expert AI job matching agent. Your role is to:

1. Extract relevant technical skills from resume text
2. Analyze job postings to find the best matches
3. Provide detailed explanations for why specific jobs are good matches
4. Offer career insights and recommendations

When analyzing resumes, focus on:
- Programming languages and frameworks
- Tools and technologies
- Years of experience indicators
- Domain expertise
- Soft skills mentioned

When matching jobs, consider:
- Skill overlap and relevance
- Seniority level match
- Industry alignment
- Location preferences (if mentioned)

Always provide clear, actionable recommendations with specific reasoning.""",
)


@agent.tool
def extract_skills_from_resume(ctx: RunContext[JobMatchingDeps], resume_text: str) -> List[str]:
    """
    Extract the most important technical skills from a resume.

    Args:
        resume_text: The full text content of a resume

    Returns:
        A list of the most important technical skills found
    """

    # Simple skill extraction logic for now
    # In a real implementation, you might use a more sophisticated approach
    common_skills = [
        "python",
        "javascript",
        "java",
        "react",
        "django",
        "flask",
        "node.js",
        "sql",
        "postgresql",
        "mysql",
        "mongodb",
        "aws",
        "azure",
        "docker",
        "kubernetes",
        "git",
        "pandas",
        "numpy",
        "scikit-learn",
        "tensorflow",
        "pytorch",
        "html",
        "css",
        "typescript",
        "vue.js",
        "angular",
        "spring",
        "express.js",
        "redis",
        "elasticsearch",
        "jenkins",
        "ci/cd",
        "restful",
        "api",
        "microservices",
        "agile",
        "scrum",
        "machine learning",
        "data analysis",
        "blockchain",
    ]

    resume_lower = resume_text.lower()
    found_skills = []

    for skill in common_skills:
        if skill in resume_lower:
            # Add the skill in proper case
            found_skills.append(skill.title() if skill.islower() else skill)

    # Remove duplicates and return top 10
    unique_skills = list(dict.fromkeys(found_skills))
    return unique_skills[:10]


@agent.tool
def find_best_job_match(ctx: RunContext[JobMatchingDeps], skills: List[str]) -> dict[str, Any]:
    """
    Find the best matching job based on extracted skills.

    Args:
        skills: List of skills extracted from resume

    Returns:
        Information about the best matching job with detailed reasoning
    """
    jobs_df = ctx.deps.jobs_df

    if jobs_df.empty or not skills:
        return {
            "error": "No jobs available or no skills provided",
            "job_title": "No match found",
            "company_name": "N/A",
            "location": "N/A",
            "match_score": 0,
            "matched_skills": [],
            "reasoning": "Unable to find matches due to missing data",
        }

    # Calculate match scores for each job
    job_scores = []
    skills_lower = [skill.lower().strip() for skill in skills]

    for index, job in jobs_df.iterrows():
        score_info = calculate_job_score(job, skills_lower)
        if score_info["score"] > 0:  # Only include jobs with some match
            job_scores.append(
                {
                    "index": index,
                    "score": score_info["score"],
                    "matched_skills": score_info["matched_skills"],
                    "job_data": job,
                }
            )

    if not job_scores:
        return {
            "error": "No matching jobs found",
            "job_title": "No suitable matches",
            "company_name": "N/A",
            "location": "N/A",
            "match_score": 0,
            "matched_skills": [],
            "reasoning": "No jobs found that match the extracted skills",
        }

    # Sort by score (highest first)
    job_scores.sort(key=lambda x: x["score"], reverse=True)

    # Get the best match
    best_match = job_scores[0]
    job_data = best_match["job_data"]

    return {
        "job_title": job_data["job_title"],
        "company_name": job_data["company_name"],
        "location": job_data["location"],
        "salary": job_data.get("salary", "Not specified"),
        "job_description": job_data.get("job_description", "")[:300] + "...",
        "match_score": best_match["score"],
        "matched_skills": best_match["matched_skills"],
        "total_jobs_analyzed": len(job_scores),
        "reasoning": f"This job scored highest ({best_match['score']} points) because it matches {len(best_match['matched_skills'])} of your key skills: {', '.join(best_match['matched_skills'])}. The role appears to be a good fit for your technical background.",
    }


@agent.tool
def get_skill_statistics(ctx: RunContext[JobMatchingDeps], skills: List[str]) -> dict[str, Any]:
    """
    Analyze how common each skill is in the job market.

    Args:
        skills: List of skills to analyze

    Returns:
        Statistics about skill demand in the job market
    """
    jobs_df = ctx.deps.jobs_df
    skill_stats = {}
    total_jobs = len(jobs_df)

    for skill in skills:
        skill_lower = skill.lower().strip()

        # Count jobs mentioning this skill
        job_count = 0
        for _, job in jobs_df.iterrows():
            job_text = ""
            if pd.notna(job.get("job_description")):
                job_text += job["job_description"].lower() + " "
            if pd.notna(job.get("job_title")):
                job_text += job["job_title"].lower() + " "

            if skill_lower in job_text:
                job_count += 1

        percentage = round((job_count / total_jobs) * 100, 1) if total_jobs > 0 else 0

        skill_stats[skill] = {
            "jobs_mentioning": job_count,
            "percentage": percentage,
            "demand_level": get_demand_level(job_count, total_jobs),
        }

    return skill_stats


@agent.tool
def find_alternative_matches(
    ctx: RunContext[JobMatchingDeps], skills: List[str], top_n: int = 5
) -> List[dict[str, Any]]:
    """
    Find multiple good job matches, not just the best one.

    Args:
        skills: List of skills from resume
        top_n: Number of top matches to return

    Returns:
        Top N matching jobs with explanations
    """
    jobs_df = ctx.deps.jobs_df

    if jobs_df.empty or not skills:
        return []

    skills_lower = [skill.lower().strip() for skill in skills]
    job_scores = []

    # Calculate scores for all jobs
    for index, job in jobs_df.iterrows():
        score_info = calculate_job_score(job, skills_lower)

        if score_info["score"] > 0:  # Only include jobs with some match
            job_scores.append(
                {
                    "job_title": job["job_title"],
                    "company_name": job["company_name"],
                    "location": job["location"],
                    "salary": job.get("salary", "Not specified"),
                    "match_score": score_info["score"],
                    "matched_skills": score_info["matched_skills"],
                    "reasoning": f"Score: {score_info['score']} - Matches {len(score_info['matched_skills'])} skills: {', '.join(score_info['matched_skills'])}",
                }
            )

    # Sort and return top N
    job_scores.sort(key=lambda x: x["match_score"], reverse=True)
    return job_scores[:top_n]


def calculate_job_score(job: pd.Series, skills: List[str]) -> dict[str, Any]:
    """
    Calculate how well a job matches the given skills.

    Args:
        job: A single job posting
        skills: Skills (already in lowercase)

    Returns:
        Score and matched skills information
    """
    # Get job text for analysis (combine title and description)
    job_text = ""
    if pd.notna(job.get("job_title")):
        job_text += job["job_title"].lower() + " "

    if pd.notna(job.get("job_description")):
        job_text += job["job_description"].lower() + " "

    if not job_text.strip():
        return {"score": 0, "matched_skills": []}

    matched_skills = []
    score = 0

    # Check each skill against job text
    for skill in skills:
        if skill in job_text:
            matched_skills.append(skill)

            # Weight skills differently based on importance
            if len(skill) <= 3:  # Short skills like "SQL", "AWS"
                score += 2
            elif skill in ["python", "javascript", "java", "react", "django"]:
                score += 3  # High-value skills
            else:
                score += 1  # Standard match

    # Bonus for multiple skill matches
    if len(matched_skills) >= 3:
        score += 2
    if len(matched_skills) >= 5:
        score += 3

    return {"score": score, "matched_skills": matched_skills}


def get_demand_level(job_count: int, total_jobs: int) -> str:
    """Categorize skill demand level"""
    if total_jobs == 0:
        return "Unknown"

    percentage = (job_count / total_jobs) * 100

    if percentage >= 50:
        return "Very High"
    elif percentage >= 25:
        return "High"
    elif percentage >= 10:
        return "Medium"
    elif percentage >= 5:
        return "Low"
    else:
        return "Very Low"


async def analyze_resume_and_find_jobs(resume_text: str, jobs_df: pd.DataFrame) -> dict[str, Any]:
    """
    Main function to analyze resume and find job matches using the AI agent.

    Args:
        resume_text: The resume text to analyze
        jobs_df: DataFrame containing job postings

    Returns:
        Complete analysis results including skills, best match, and alternatives
    """
    try:
        # Create the dependencies object
        deps = JobMatchingDeps(jobs_df=jobs_df)

        # Create the main prompt for the agent
        prompt = f"""
        Please help me find the best job matches for this resume. I need you to:

        1. Extract the most important technical skills from the resume
        2. Find the best matching job from the available postings
        3. Provide alternative job matches (top 5)
        4. Analyze the demand for the extracted skills in the job market

        Please use the available tools to complete this analysis and provide a comprehensive summary with your reasoning for why the recommended job is the best match.

        Resume text:
        {resume_text}
        """

        # Run the agent with the dependencies
        result = await agent.run(prompt, deps=deps)

        return {
            "success": True,
            "analysis": result.output,
            "all_messages": result.all_messages(),  # This will show what tools were called
        }

    except Exception as e:
        return {"success": False, "error": str(e), "analysis": None}


def analyze_resume_and_find_jobs_sync(resume_text: str, jobs_df: pd.DataFrame) -> dict[str, Any]:
    """
    Synchronous version of the main analysis function.

    Args:
        resume_text: The resume text to analyze
        jobs_df: DataFrame containing job postings

    Returns:
        Complete analysis results including skills, best match, and alternatives
    """
    try:
        # Create the dependencies object
        deps = JobMatchingDeps(jobs_df=jobs_df)

        # Create the main prompt for the agent
        prompt = f"""
        Please help me find the best job matches for this resume. I need you to:

        1. Extract the most important technical skills from the resume
        2. Find the best matching job from the available postings
        3. Provide alternative job matches (top 5)
        4. Analyze the demand for the extracted skills in the job market

        Please use the available tools to complete this analysis and provide a comprehensive summary with your reasoning for why the recommended job is the best match.

        Resume text:
        {resume_text}
        """

        # Run the agent with the dependencies
        result = agent.run_sync(prompt, deps=deps)

        return {
            "success": True,
            "analysis": result.output,
            "all_messages": result.all_messages(),  # This will show what tools were called
            "agent_result": result,  # Store the full result for conversation continuation
        }

    except Exception as e:
        return {"success": False, "error": str(e), "analysis": None}


def continue_conversation_sync(
    follow_up_question: str, previous_result, jobs_df: pd.DataFrame
) -> dict[str, Any]:
    """
    Continue the conversation with the AI agent using the previous context.

    Args:
        follow_up_question: The follow-up question to ask
        previous_result: The previous agent result object
        jobs_df: DataFrame containing job postings

    Returns:
        Follow-up response from the agent
    """
    try:
        # Create the dependencies object
        deps = JobMatchingDeps(jobs_df=jobs_df)

        # Create a new agent run that continues from the previous conversation
        # We'll use the message history to maintain context
        result = agent.run_sync(
            follow_up_question, deps=deps, message_history=previous_result.all_messages()
        )

        return {
            "success": True,
            "response": result.output,
            "all_messages": result.all_messages(),
            "agent_result": result,
        }

    except Exception as e:
        return {"success": False, "error": str(e), "response": None}


# Validation functions (keeping from original for compatibility)
def validate_resume_text(resume_text: str) -> dict[str, Any]:
    """
    Validate that resume text is suitable for processing.

    Args:
        resume_text: Resume text to validate

    Returns:
        Validation results and suggestions
    """
    issues = []
    warnings = []

    # Check basic requirements
    if not resume_text or not resume_text.strip():
        issues.append("Resume text is empty")
        return {"valid": False, "issues": issues, "warnings": warnings}

    # Check length
    word_count = len(resume_text.split())
    if word_count < 50:
        warnings.append("Resume seems quite short - consider adding more detail")
    elif word_count > 2000:
        warnings.append("Resume is very long - extraction might focus on early sections")

    # Check for common sections
    resume_lower = resume_text.lower()
    expected_sections = ["experience", "skills", "education", "work"]
    found_sections = [section for section in expected_sections if section in resume_lower]

    if len(found_sections) < 2:
        warnings.append("Resume might be missing common sections (experience, skills, education)")

    # Check for technical content
    tech_indicators = [
        "python",
        "javascript",
        "programming",
        "software",
        "development",
        "technical",
    ]
    tech_mentions = sum(1 for indicator in tech_indicators if indicator in resume_lower)

    if tech_mentions == 0:
        warnings.append("No technical skills detected - results may be limited")

    return {
        "valid": True,
        "word_count": word_count,
        "sections_found": found_sections,
        "tech_indicators": tech_mentions,
        "issues": issues,
        "warnings": warnings,
    }

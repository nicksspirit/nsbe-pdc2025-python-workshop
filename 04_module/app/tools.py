import os
from typing import Any

import pandas as pd
from pydantic_ai import Agent
from pydantic_ai.models.google import GoogleModel
from pydantic_ai.providers.google import GoogleProvider

# Set up the AI model for our tools
# Note: You'll need to set your Google API key as an environment variable
# Using gemini-2.5-flash - Google's latest, fastest model with excellent reasoning
provider = GoogleProvider(api_key=os.getenv("GOOGLE_API_KEY"))
model = GoogleModel("gemini-2.5-flash")

# Create our agent instance
agent = Agent(model=model)

# <START> EXTRACT SKILLS


def extract_skills_from_resume(resume_text: str, top_n: int = 10) -> list[str]:
    """
    Extract the top technical skills from a resume using AI.

    Args:
        resume_text (str): The full text content of a resume

    Returns:
        list[str]: A list of the most important technical skills found
    """

    # Create a focused prompt for skill extraction
    prompt = f"""
    Please analyze this resume and extract the top {top_n} most important technical skills.
    Focus on:
    - Programming languages (Python, JavaScript, etc.)
    - Frameworks and libraries (React, Django, etc.)
    - Tools and technologies (Git, Docker, AWS, etc.)
    - Data analysis tools (Pandas, SQL, etc.)
    - Any other technical competencies

    Return only the skill names, one per line, without explanations.
    Be specific (e.g., "Python" not "programming languages").

    Resume text:
    {resume_text}
    """

    # Use the agent to process the prompt
    result = agent.run_sync(prompt)
    skills_text = result.output

    # Split by lines and clean up
    skills = [
        skill.strip().strip("-•*").strip()
        for skill in skills_text.split("\n")
        if skill.strip() and len(skill.strip()) > 1
    ]

    # Remove duplicates while preserving order
    unique_skills = set(skill.lower() for skill in skills)

    return list(unique_skills)[:top_n]  # Return top N skills


# <END> EXTRACT SKILLS

# <START> JOB MATCHING


def find_best_job_match(skills: list[str], jobs_df: pd.DataFrame) -> dict[str, Any]:
    """
    Find the best matching job based on extracted skills.

    Args:
        skills (list[str]): List of skills extracted from resume
        jobs_df (pd.DataFrame): DataFrame containing job postings

    Returns:
        dict[str, Any]: Information about the best matching job
    """

    if jobs_df.empty or not skills:
        return {
            "error": "No jobs available or no skills provided",
            "job_title": "No match found",
            "company_name": "N/A",
            "location": "N/A",
            "match_score": 0,
            "matched_skills": [],
        }

    # Note: skills are already lowercase from extract_skills_from_resume

    # Calculate match scores for each job
    job_scores = []

    for index, job in jobs_df.iterrows():
        score_info = calculate_job_score(job, skills)
        job_scores.append(
            {
                "index": index,
                "score": score_info["score"],
                "matched_skills": score_info["matched_skills"],
                "job_data": job,
            }
        )

    # Sort by score (highest first)
    job_scores.sort(key=lambda x: x["score"], reverse=True)

    if not job_scores or job_scores[0]["score"] == 0:
        return {
            "error": "No matching jobs found",
            "job_title": "No suitable matches",
            "company_name": "N/A",
            "location": "N/A",
            "match_score": 0,
            "matched_skills": [],
        }

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
    }


def calculate_job_score(job: pd.Series, skills: list[str]) -> dict[str, Any]:
    """
    Calculate how well a job matches the given skills.

    Args:
        job (pd.Series): A single job posting
        skills (list[str]): Skills (already in lowercase)

    Returns:
        dict[str, Any]: Score and matched skills information
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


# <END> JOB MATCHING

# <START> ADDITIONAL TOOLS


def get_skill_statistics(skills: list[str], jobs_df: pd.DataFrame) -> dict[str, Any]:
    """
    Analyze how common each skill is in the job market.

    Args:
        skills (list[str]): List of skills to analyze
        jobs_df (pd.DataFrame): Job postings database

    Returns:
        dict[str, Any]: Statistics about skill demand
    """

    # Combine all job text for analysis
    all_job_text = ""
    for _, job in jobs_df.iterrows():
        if pd.notna(job.get("job_description")):
            all_job_text += job["job_description"].lower() + " "
        if pd.notna(job.get("job_title")):
            all_job_text += job["job_title"].lower() + " "

    skill_stats = {}
    total_jobs = len(jobs_df)

    for skill in skills:
        skill_lower = skill.lower()

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

        skill_stats[skill] = {
            "jobs_mentioning": job_count,
            "percentage": round((job_count / total_jobs) * 100, 1) if total_jobs > 0 else 0,
            "demand_level": get_demand_level(job_count, total_jobs),
        }

    return skill_stats


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


def find_alternative_matches(
    skills: list[str], jobs_df: pd.DataFrame, top_n: int = 5
) -> list[dict[str, Any]]:
    """
    Find multiple good job matches, not just the best one.

    Args:
        skills (list[str]): List of skills from resume
        jobs_df (pd.DataFrame): Job postings database
        top_n (int): Number of top matches to return

    Returns:
        list[dict[str, Any]]: Top N matching jobs
    """

    if jobs_df.empty or not skills:
        return []

    skills_lower = [skill.lower() for skill in skills]
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
                }
            )

    # Sort and return top N
    job_scores.sort(key=lambda x: x["match_score"], reverse=True)
    return job_scores[:top_n]


# <END> ADDITIONAL TOOLS

# <START> Error Handling


def validate_resume_text(resume_text: str) -> dict[str, Any]:
    """
    Validate that resume text is suitable for processing.

    Args:
        resume_text (str): Resume text to validate

    Returns:
        dict[str, Any]: Validation results and suggestions
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


def safe_extract_skills(resume_text: str) -> dict[str, Any]:
    """
    Safely extract skills with comprehensive error handling.

    Args:
        resume_text (str): Resume text to process

    Returns:
        dict[str, Any]: Results including skills and any issues
    """

    # Validate input
    validation = validate_resume_text(resume_text)

    if not validation["valid"]:
        return {
            "success": False,
            "skills": [],
            "issues": validation["issues"],
            "warnings": validation["warnings"],
        }

    try:
        # Attempt skill extraction
        skills = extract_skills_from_resume(resume_text)

        return {
            "success": True,
            "skills": skills,
            "skill_count": len(skills),
            "word_count": validation["word_count"],
            "issues": validation["issues"],
            "warnings": validation["warnings"],
        }

    except Exception as e:
        return {
            "success": False,
            "skills": [],
            "error": str(e),
            "issues": validation["issues"] + [f"Processing error: {str(e)}"],
            "warnings": validation["warnings"],
        }


# <END> ADDITIONAL TOOLS

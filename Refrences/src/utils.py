import logging

# Configure logging settings
logging.basicConfig(
    level=logging.INFO,  # Change to DEBUG for more verbose logging
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def setup_logger(name):
    """
    Set up a logger with a specific name.
    
    Parameters:
        name (str): The name of the logger.
    
    Returns:
        logging.Logger: Configured logger object.
    """
    logger = logging.getLogger(name)
    return logger

def validate_date(date_str):
    """
    Validate a date string in YYYY-MM-DD format.

    Parameters:
        date_str (str): The date string to validate.

    Returns:
        bool: True if the date is valid, False otherwise.
    """
    from datetime import datetime
    try:
        datetime.strptime(date_str, '%Y-%m-%d')
        return True
    except ValueError:
        return False

def clean_column_names(df):
    """
    Clean DataFrame column names by removing leading/trailing spaces and converting to lowercase.

    Parameters:
        df (pd.DataFrame): The DataFrame with column names to clean.

    Returns:
        pd.DataFrame: DataFrame with cleaned column names.
    """
    df.columns = [col.strip().lower().replace(" ", "_") for col in df.columns]
    return df

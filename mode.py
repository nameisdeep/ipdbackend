import pandas as pd
import pickle

# Example new input data
new_data = {
    'Day_of_Week': [2],  # Tuesday
    'Month': [1],  # January
    'Working_Hours': [8],  # 8 hours
    'Crop_Type': ['Wheat'],  # Crop type
    'Base_Hourly_Wage': [12.00],  # Base hourly wage
    'Supply_Demand_Ratio': [1.2],  # Supply-demand ratio
    'Dynamic_Pricing_Multiplier': [1.44]  # Dynamic pricing multiplier
}

# Convert the new input data into a DataFrame
new_input_df = pd.DataFrame(new_data)

# Load the trained model from the file
with open('ann_model.pkl', 'rb') as file:
    loaded_model = pickle.load(file)

# Make predictions using the loaded model
predicted_earnings = loaded_model.predict(new_input_df)

# Output the prediction
print(predicted_earnings)

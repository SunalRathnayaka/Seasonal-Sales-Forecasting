import pandas as pd
import numpy as np
import json
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
import xgboost as xgb
import holidays
import os
from sklearn.metrics import mean_absolute_error, mean_squared_error
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler

class SalesForecaster:
    def __init__(self, input_file, output_dir='./output'):
        """Initialize the sales forecaster with input and output paths"""
        self.input_file = input_file
        self.output_dir = output_dir
        self.forecast = None
        self.model = None
        self.data = None
        self.processed_data = None
        self.feature_cols = []
        self.scaler = StandardScaler()
        
        # Create output directory if it doesn't exist
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
    
    def load_data(self):
        """Load weekly sales data from JSON file"""
        try:
            with open(self.input_file, 'r') as file:
                raw_data = json.load(file)
                
            # Assuming the JSON structure has records with date and sales
            if isinstance(raw_data, list):
                self.data = pd.DataFrame(raw_data)
            elif isinstance(raw_data, dict):
                # Handle case where JSON might be nested
                if 'sales_data' in raw_data:
                    self.data = pd.DataFrame(raw_data['sales_data'])
                else:
                    # Try to convert flat dictionary to dataframe
                    self.data = pd.DataFrame([raw_data])
            
            print(f"Data loaded successfully with {len(self.data)} records")
            
            # Debug: show data sample
            print("Sample data:")
            print(self.data.head())
            
            return True
        except Exception as e:
            print(f"Error loading data: {e}")
            return False
    
    def preprocess_data(self):
        """Preprocess the loaded data for XGBoost format"""
        if self.data is None:
            print("No data loaded. Please call load_data() first.")
            return False
        
        # Make a copy to avoid modifying the original data
        working_data = self.data.copy()
        
        # Check for required columns
        required_cols = {'date', 'sales'}
        if not all(col in working_data.columns for col in required_cols):
            # Try to identify and rename columns
            date_cols = [col for col in working_data.columns if 'date' in col.lower() or 'week' in col.lower()]
            sales_cols = [col for col in working_data.columns if 'sales' in col.lower() or 'revenue' in col.lower()]
            
            if date_cols and sales_cols:
                working_data = working_data.rename(columns={
                    date_cols[0]: 'date',
                    sales_cols[0]: 'sales'
                })
            else:
                print("Required columns 'date' and 'sales' not found")
                return False
        
        # Convert date column to datetime
        try:
            working_data['date'] = pd.to_datetime(working_data['date'])
        except Exception as e:
            print(f"Error converting date column to datetime: {e}")
            return False
        
        # Sort by date
        working_data = working_data.sort_values('date')
        
        # Ensure sales is numeric
        working_data['sales'] = pd.to_numeric(working_data['sales'], errors='coerce')
        
        # Check if we have valid numeric sales
        if working_data['sales'].isna().all():
            print("Error: All sales values are invalid or could not be converted to numbers")
            return False
        
        # Remove rows with NaN sales values
        working_data = working_data.dropna(subset=['sales'])
        
        print(f"After cleaning: {len(working_data)} records with valid sales data")
        
        # Store the processed data
        self.processed_data = working_data
        
        # Debug: show processed data info
        print(f"Processed data: {len(self.processed_data)} rows")
        print(f"Data types: {self.processed_data.dtypes}")
        print(f"Any NaN values: {self.processed_data.isna().any()}")
        print(f"First few rows of processed data:")
        print(self.processed_data.head())
        
        start_date = working_data['date'].min()
        end_date = working_data['date'].max()
        print(f"Data preprocessed successfully, spanning from {start_date.date()} to {end_date.date()}")
        return True
    
    def add_features(self):
        """Add features for XGBoost including lags and seasonality"""
        if self.processed_data is None or len(self.processed_data) == 0:
            print("No valid processed data available. Please check preprocess_data() results.")
            return False
        
        df = self.processed_data.copy()
        
        # Add date-based features
        df['year'] = df['date'].dt.year
        df['month'] = df['date'].dt.month
        df['week_of_year'] = df['date'].dt.isocalendar().week
        df['day_of_week'] = df['date'].dt.dayofweek
        
        # Add lag features (previous weeks' sales)
        for lag in range(1, 13):  # Use lags 1 to 12 weeks
            if len(df) > lag:
                df[f'sales_lag_{lag}'] = df['sales'].shift(lag)
        
        # Add rolling window features
        if len(df) > 4:
            df['sales_rolling_mean_4'] = df['sales'].shift(1).rolling(window=4).mean()
        if len(df) > 8:
            df['sales_rolling_mean_8'] = df['sales'].shift(1).rolling(window=8).mean()
        if len(df) > 12:
            df['sales_rolling_mean_12'] = df['sales'].shift(1).rolling(window=12).mean()
        
        # Add holiday indicators
        try:
            us_holidays = holidays.US()
            df['is_holiday'] = df['date'].map(lambda x: 1 if x in us_holidays else 0)
            
            # Add holiday proximity (days before/after major holidays)
            major_holidays = ['Christmas', 'New Year', 'Thanksgiving', 'Independence Day']
            df['holiday_proximity'] = 0
            
            for date, name in us_holidays.items():
                if any(holiday in name for holiday in major_holidays):
                    holiday_date = pd.Timestamp(date)
                    # Find closest date in our dataset
                    for idx, row in df.iterrows():
                        days_diff = abs((row['date'] - holiday_date).days)
                        if days_diff <= 14:  # Within 2 weeks
                            proximity_score = max(0, (14 - days_diff) / 14)
                            df.at[idx, 'holiday_proximity'] = max(df.at[idx, 'holiday_proximity'], proximity_score)
        except Exception as e:
            print(f"Warning: Could not add holiday features: {e}")
            df['is_holiday'] = 0
            df['holiday_proximity'] = 0
        
        # Add seasonal indicators (sine and cosine transformations for cyclical features)
        # This captures yearly seasonality
        df['sin_month'] = np.sin(2 * np.pi * df['month'] / 12)
        df['cos_month'] = np.cos(2 * np.pi * df['month'] / 12)
        
        # Weekly seasonality
        df['sin_day'] = np.sin(2 * np.pi * df['day_of_week'] / 7)
        df['cos_day'] = np.cos(2 * np.pi * df['day_of_week'] / 7)
        
        # Drop rows with NaN values (from lag creation)
        df = df.dropna()
        
        # Store the feature-engineered data
        self.feature_data = df
        
        # Define feature columns (exclude date and target)
        self.feature_cols = [col for col in df.columns if col not in ['date', 'sales']]
        
        print(f"Feature engineering complete. Data shape: {df.shape}")
        print(f"Created {len(self.feature_cols)} features: {self.feature_cols}")
        
        return True
    
    def train_model(self):
        """Train the XGBoost forecasting model"""
        if self.feature_data is None or len(self.feature_data) < 5:
            print("Not enough data for training after feature engineering")
            return False
        
        # Prepare data for training
        X = self.feature_data[self.feature_cols]
        y = self.feature_data['sales']
        
        # Normalize features for better performance
        X_scaled = self.scaler.fit_transform(X)
        
        # Split data into training and validation sets
        # Use a temporal split since this is time series data
        train_size = int(len(X) * 0.8)
        X_train, X_val = X_scaled[:train_size], X_scaled[train_size:]
        y_train, y_val = y[:train_size], y[train_size:]
        
        # Define XGBoost model
        self.model = xgb.XGBRegressor(
            objective='reg:squarederror',
            n_estimators=100,
            max_depth=4,
            learning_rate=0.1,
            subsample=0.8,
            colsample_bytree=0.8,
            random_state=42
        )
        
        # Train the model
        try:
            self.model.fit(
                X_train, y_train,
                eval_set=[(X_val, y_val)],
                eval_metric='rmse',
                early_stopping_rounds=10,
                verbose=False
            )
            
            # Get feature importance
            importance = self.model.feature_importances_
            feature_importance = pd.DataFrame({
                'feature': self.feature_cols,
                'importance': importance
            }).sort_values('importance', ascending=False)
            
            print("\nTop 10 important features:")
            print(feature_importance.head(10))
            
            # Evaluate on validation set
            val_pred = self.model.predict(X_val)
            val_rmse = np.sqrt(mean_squared_error(y_val, val_pred))
            val_mae = mean_absolute_error(y_val, val_pred)
            
            print(f"Validation RMSE: {val_rmse:.2f}")
            print(f"Validation MAE: {val_mae:.2f}")
            
            return True
        except Exception as e:
            print(f"Error training model: {e}")
            return False
    
    def generate_forecast(self, weeks=12):
        """Generate forecast for the specified number of weeks"""
        if self.model is None:
            print("No model available. Please call train_model() first.")
            return False
        
        # Start with the last data point we have
        last_data = self.feature_data.iloc[-1].copy()
        last_date = last_data['date']
        
        # Create forecast dataframe
        forecast_dates = [last_date + timedelta(weeks=i+1) for i in range(weeks)]
        forecast_df = pd.DataFrame({'date': forecast_dates})
        
        # Add date-based features
        forecast_df['year'] = forecast_df['date'].dt.year
        forecast_df['month'] = forecast_df['date'].dt.month
        forecast_df['week_of_year'] = forecast_df['date'].dt.isocalendar().week
        forecast_df['day_of_week'] = forecast_df['date'].dt.dayofweek
        
        # Add seasonal indicators
        forecast_df['sin_month'] = np.sin(2 * np.pi * forecast_df['month'] / 12)
        forecast_df['cos_month'] = np.cos(2 * np.pi * forecast_df['month'] / 12)
        forecast_df['sin_day'] = np.sin(2 * np.pi * forecast_df['day_of_week'] / 7)
        forecast_df['cos_day'] = np.cos(2 * np.pi * forecast_df['day_of_week'] / 7)
        
        # Add holiday indicators
        try:
            us_holidays = holidays.US()
            forecast_df['is_holiday'] = forecast_df['date'].map(lambda x: 1 if x in us_holidays else 0)
            
            # Add holiday proximity
            major_holidays = ['Christmas', 'New Year', 'Thanksgiving', 'Independence Day']
            forecast_df['holiday_proximity'] = 0
            
            for date, name in us_holidays.items():
                if any(holiday in name for holiday in major_holidays):
                    holiday_date = pd.Timestamp(date)
                    for idx, row in forecast_df.iterrows():
                        days_diff = abs((row['date'] - holiday_date).days)
                        if days_diff <= 14:  # Within 2 weeks
                            proximity_score = max(0, (14 - days_diff) / 14)
                            forecast_df.at[idx, 'holiday_proximity'] = max(
                                forecast_df.at[idx, 'holiday_proximity'], proximity_score)
        except Exception as e:
            print(f"Warning: Could not add holiday features to forecast: {e}")
            forecast_df['is_holiday'] = 0
            forecast_df['holiday_proximity'] = 0
        
        # Recursively generate forecasts
        predictions = []
        prediction_intervals = []
        
        # Create a rolling window of data that we'll update as we make predictions
        rolling_data = self.feature_data.iloc[-12:].copy()  # Last 12 weeks of actual data
        
        for i in range(weeks):
            # Prepare the next week's features
            next_week = forecast_df.iloc[i].copy()
            
            # Add lag features from our rolling window
            for lag in range(1, 13):
                if lag <= len(rolling_data):
                    next_week[f'sales_lag_{lag}'] = rolling_data.iloc[-lag]['sales']
                else:
                    next_week[f'sales_lag_{lag}'] = np.nan
            
            # Add rolling means
            if len(rolling_data) >= 4:
                next_week['sales_rolling_mean_4'] = rolling_data['sales'].iloc[-4:].mean()
            else:
                next_week['sales_rolling_mean_4'] = np.nan
                
            if len(rolling_data) >= 8:
                next_week['sales_rolling_mean_8'] = rolling_data['sales'].iloc[-8:].mean()
            else:
                next_week['sales_rolling_mean_8'] = np.nan
                
            if len(rolling_data) >= 12:
                next_week['sales_rolling_mean_12'] = rolling_data['sales'].iloc[-12:].mean()
            else:
                next_week['sales_rolling_mean_12'] = np.nan
            
            # Fill any missing values with the mean of available data
            for col in self.feature_cols:
                if col in next_week and pd.isna(next_week[col]):
                    if col in rolling_data.columns:
                        next_week[col] = rolling_data[col].mean()
                    else:
                        next_week[col] = 0
            
            # Prepare input for the model
            X_next = np.array([next_week[col] for col in self.feature_cols]).reshape(1, -1)
            X_next_scaled = self.scaler.transform(X_next)
            
            # Make prediction
            pred = self.model.predict(X_next_scaled)[0]
            
            # Create a simple confidence interval (±10% of the prediction)
            lower_bound = pred * 0.9
            upper_bound = pred * 1.1
            
            # Store prediction
            predictions.append(pred)
            prediction_intervals.append((lower_bound, upper_bound))
            
            # Update the rolling data with this prediction
            new_row = next_week.copy()
            new_row['sales'] = pred
            rolling_data = pd.concat([rolling_data, pd.DataFrame([new_row])], ignore_index=True)
            rolling_data = rolling_data.iloc[1:]  # Remove the oldest entry
        
        # Create forecast dataframe
        self.forecast = pd.DataFrame({
            'ds': forecast_dates,
            'yhat': predictions,
            'yhat_lower': [interval[0] for interval in prediction_intervals],
            'yhat_upper': [interval[1] for interval in prediction_intervals]
        })
        
        print(f"Generated forecast for {weeks} weeks from {last_date.date()} to {forecast_dates[-1].date()}")
        return True
    
    def evaluate_model(self):
        """Evaluate model performance using time-series cross validation"""
        if self.model is None or self.feature_data is None:
            print("Model or feature data not available")
            return False
        
        # Use time series cross-validation to evaluate model
        # We'll use the last 20% of data for testing if we have enough data
        n_samples = len(self.feature_data)
        
        if n_samples < 10:
            print("Not enough data for proper evaluation")
            return {'MAE': 0, 'RMSE': 0, 'MAPE': 0}
        
        test_size = max(1, int(n_samples * 0.2))  # At least 1 sample
        train_data = self.feature_data.iloc[:-test_size]
        test_data = self.feature_data.iloc[-test_size:]
        
        # Train a model on training data
        X_train = train_data[self.feature_cols]
        y_train = train_data['sales']
        X_train_scaled = self.scaler.transform(X_train)
        
        X_test = test_data[self.feature_cols]
        y_test = test_data['sales']
        X_test_scaled = self.scaler.transform(X_test)
        
        # Train a model for evaluation
        eval_model = xgb.XGBRegressor(
            objective='reg:squarederror',
            n_estimators=100,
            max_depth=4,
            learning_rate=0.1,
            subsample=0.8,
            colsample_bytree=0.8,
            random_state=42
        )
        eval_model.fit(X_train_scaled, y_train)
        
        # Make predictions
        y_pred = eval_model.predict(X_test_scaled)
        
        # Calculate metrics
        mae = mean_absolute_error(y_test, y_pred)
        rmse = np.sqrt(mean_squared_error(y_test, y_pred))
        mape = np.mean(np.abs((y_test - y_pred) / y_test)) * 100
        
        evaluation = {
            'MAE': mae,
            'RMSE': rmse,
            'MAPE': mape
        }
        
        print(f"Model Evaluation: MAE={mae:.2f}, RMSE={rmse:.2f}, MAPE={mape:.2f}%")
        return evaluation
    
    def export_results(self):
        """Export the forecast results to JSON and CSV"""
        if self.forecast is None:
            print("No forecast available. Please call generate_forecast() first.")
            return False
        
        # Prepare output dataframe with selected columns
        output_df = self.forecast.copy()
        output_df.rename(columns={
            'ds': 'date',
            'yhat': 'predicted_sales',
            'yhat_lower': 'lower_bound',
            'yhat_upper': 'upper_bound'
        }, inplace=True)
        
        # Convert date to string for JSON
        output_df['date'] = output_df['date'].dt.strftime('%Y-%m-%d')
        
        # Export to CSV
        csv_path = os.path.join(self.output_dir, 'sales_forecast.csv')
        output_df.to_csv(csv_path, index=False)
        
        # Export to JSON
        json_path = os.path.join(self.output_dir, 'sales_forecast.json')
        output_df.to_json(json_path, orient='records', date_format='iso')
        
        print(f"Results exported to {csv_path} and {json_path}")
        return True
    
    def plot_forecast(self):
        """Plot the forecast with historical data"""
        if self.model is None or self.forecast is None or self.processed_data is None:
            print("Model, forecast, or data not available")
            return False
        
        # Create figure
        fig, ax = plt.subplots(figsize=(12, 6))
        
        # Plot historical data
        ax.plot(self.processed_data['date'], self.processed_data['sales'], 'k.', label='Historical Sales')
        
        # Plot forecast
        ax.plot(self.forecast['ds'], self.forecast['yhat'], 'b-', label='Forecast')
        
        # Plot confidence interval
        ax.fill_between(self.forecast['ds'], 
                         self.forecast['yhat_lower'], 
                         self.forecast['yhat_upper'], 
                         color='blue', alpha=0.2, label='Confidence Interval')
        
        # Add labels and title
        ax.set_xlabel('Date')
        ax.set_ylabel('Sales')
        ax.set_title('Weekly Sales Forecast with XGBoost')
        ax.legend()
        ax.grid(True)
        
        # Add current date to the plot
        current_date = "2025-08-28"  # Using the date provided by the user
        plt.figtext(0.01, 0.01, f"Generated on: {current_date}", fontsize=8)
        
        # Save figure
        fig_path = os.path.join(self.output_dir, 'sales_forecast.png')
        plt.savefig(fig_path)
        plt.close()
        
        print(f"Forecast plot saved to {fig_path}")
        return True
    
    def run_complete_pipeline(self, weeks=12):
        """Run the complete forecasting pipeline"""
        steps = [
            self.load_data,
            self.preprocess_data,
            self.add_features,
            self.train_model,
            lambda: self.evaluate_model(),  # Wrap evaluation as it returns a dict
            lambda: self.generate_forecast(weeks),
            self.export_results,
            self.plot_forecast
        ]
        
        # Run each step and continue even if one fails
        for step in steps:
            try:
                result = step()
                # Only print failures, success messages are handled by each method
                if result is False:
                    print(f"Step {step.__name__} failed")
            except Exception as e:
                print(f"Error in {step.__name__}: {e}")
        
        if self.forecast is not None:
            print("Forecasting pipeline completed successfully")
            return True
        else:
            print("Forecasting pipeline encountered errors, no forecast generated")
            return False

# Example usage
if __name__ == "__main__":
    forecaster = SalesForecaster('weekly_sales_data.json')
    forecaster.run_complete_pipeline(weeks=52)
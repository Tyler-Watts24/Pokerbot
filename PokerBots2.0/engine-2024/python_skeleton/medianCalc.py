import pickle
#open table
with open('allHandChances.pkl', 'rb') as file:
     allHandChances = pickle.load(file)

odds_values = list(allHandChances.values())

#sort
sorted_odds = sorted(odds_values)

# Find the median
n = len(sorted_odds)
if n % 2 == 1:
    # If the number of elements is odd, return the middle element
    median_odds = sorted_odds[n // 2]
else:
    # If the number of elements is even, return the average of the two middle elements
    median_odds = (sorted_odds[n // 2 - 1] + sorted_odds[n // 2]) / 2

# Calculate Q3 (75th percentile)
def manual_percentile(data, percentile):
    n = len(data)
    index = (n - 1) * percentile
    floor = int(index)
    fraction = index - floor
    return data[floor] + fraction * (data[floor + 1] - data[floor])

print(manual_percentile(sorted_odds, 0.75))
print(median_odds)
print(manual_percentile(sorted_odds, 0.25))
print(manual_percentile(sorted_odds, .10))
print(manual_percentile(sorted_odds, .90))
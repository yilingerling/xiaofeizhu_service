arr = [1,2,3,4,5,6,7,8,9]
page = 2
page_size = 2
user_data = arr[(page - 1) * page_size: page * page_size]

print(user_data)
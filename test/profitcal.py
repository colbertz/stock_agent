from backtest import parse_suggestion

def profitcal():
    #load data from backtest_report.txt
    with open("backtest_report.txt", "r", encoding="utf-8") as f:
        lines = f.readlines()

    #loop lines with index
    cash_balance = 0
    for i, line in enumerate(lines):
        if line.startswith("<Suggestion>"):
            action, quantity = parse_suggestion(line)
            if action == "等待":
                continue
            elif action == "买入":
                # find the next line with <Data> to get the price
                userstock_line = lines[i+1][11:-13]  # remove <UserStock> and </UserStock>
                holding = int(userstock_line.split(' ')[0][2:])  # extract holding

                data_line = lines[i+2][6:-7]  # remove <Data> and </Data>
                price = float(data_line.split(',')[1]) 
                close_price = float(data_line.split(',')[2]) 
                cash_balance -= price * quantity
                print(f"Bought {quantity} shares at price {price}, cash_balance now {cash_balance}, holding now {holding} shares value {holding * close_price}, balance now {cash_balance + holding * close_price}")
            elif action == "卖出":
                userstock_line = lines[i+1][11:-13]  # remove <UserStock> and </UserStock>
                holding = int(userstock_line.split(' ')[0][2:])  # extract holding

                # find the next line with <Data> to get the price
                data_line = lines[i+2][6:-7]  # remove <Data> and </Data>
                price = float(data_line.split(',')[1]) 
                close_price = float(data_line.split(',')[2]) 
                cash_balance += price * quantity
                print(f"Sold {quantity} shares at price {price}, cash_balance now {cash_balance}, holding now {holding} shares value {holding * close_price}, balance now {cash_balance + holding * close_price}")
    
    #from end of lines, loop lines wiht index
    #find the last line with <UserStock> to get the final holding
    for j in range(len(lines)-1, -1, -1):
        if lines[j].startswith("<UserStock>"):
            # extract holding and remaining quota from <UserStock>持有{holding} 剩余仓位{remaining_quota}</UserStock>
            userstock_line = lines[j][11:-13]  # remove <UserStock> and </UserStock>
            holding = int(userstock_line.split(' ')[0][2:])  # extract holding
            # get close price from the next line with <Data>
            data_line = lines[j+1][6:-7]  # remove <Data> and </Data>
            close_price = float(data_line.split(',')[2])
            balance = cash_balance + holding * close_price
            print(f"Final holding {holding} shares value: {holding * price}, cash_balance now {cash_balance}, balance now {balance}")
            break

if __name__ == "__main__":
    profitcal()
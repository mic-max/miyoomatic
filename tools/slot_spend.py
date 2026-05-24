# Python
import math

def minimize_leftover(totalCoins, costs):
    dp = [math.inf] * (totalCoins + 1) # min number of purchases to reach c
    parent = [-1] * (totalCoins + 1)
    dp[0] = 0 # 0 purchases needed to be leftover with 0 coins?
    
    for c in range(1, totalCoins + 1):
        for i, cost in enumerate(costs):
            if c - cost >= 0 and dp[c - cost] + 1 < dp[c]:
                dp[c] = dp[c - cost] + 1
                parent[c] = i
    
    # Find max spendable with minimum purchases
    spent = -1
    best_purchases = math.inf
    for c in range(totalCoins, -1, -1):
        if dp[c] != math.inf:
            spent = c
            best_purchases = dp[c]
            break
    
    leftover = totalCoins - spent
    
    # Reconstruct chosen items
    chosen = []
    cur = spent
    while cur > 0:
        item = parent[cur]
        if item == -1:
            break
        chosen.append(costs[item])
        cur -= costs[item]
    
    return leftover, best_purchases, chosen


totalCoins = 2330
costs = [180, 500, 800, 1000, 1600, 2800, 3500, 4000, 4500, 5500, 9999]
# some items have the same cost so show the user they can buy 3 of any combination of [a, b, c]

mostLeftover = -1

for totalCoins in range(180, 10000):
    leftover, purchases, chosen = minimize_leftover(totalCoins, costs)
    print(totalCoins, leftover, len(chosen))
    # print("Leftover:", leftover)
    # print("Purchases:", purchases)
    # counts = collections.Counter(chosen)
    # for cost, count in sorted(counts.items()):
    #     print(f"{count} × item costing {cost}")

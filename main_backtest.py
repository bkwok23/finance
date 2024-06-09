import statistics_lib as stat
import optimization_lib as opt

import datetime as dt
import pandas as pd

if __name__ == '__main__':
    training_end_period = "2023-12-29"
    testing_start_period = "2024-01-03"

    benchmark_wt = {"BNS CN": 1/6, "BMO CN": 1/6, "TD CN": 1/6, "CM CN": 1/6, "RY CN": 1/6, "NA CN": 1/6, "cash": 0}

    _cash = 50/1e4
    default_portfolio_wt = {"BNS CN": (1-_cash)/6, "BMO CN": (1-_cash)/6, "TD CN": (1-_cash)/6, "CM CN": (1-_cash)/6, "RY CN": (1-_cash)/6, "NA CN": (1-_cash)/6, "cash": _cash}
    df_returns_matrix = stat.calc_returns_matrix(sec_list=list(benchmark_wt.keys()), start_date=dt.datetime(2018, 11, 16))

    # backtest portfolios
    bench = stat.calc_port_return(dates_list=pd.to_datetime(df_returns_matrix.loc[testing_start_period:].index), initial_ticker_weights=benchmark_wt, tr_matrix=df_returns_matrix)
    default = stat.calc_port_return(dates_list=pd.to_datetime(df_returns_matrix.loc[testing_start_period:].index), initial_ticker_weights=default_portfolio_wt, tr_matrix=df_returns_matrix)

    # Find the optimized portfolio to replicate the benchmark given the cash drag

    # no rebalance
    sol = opt.minimize_active_risk(benchmark_portfolio=benchmark_wt, cash_drag=_cash, tr_matrix=df_returns_matrix.loc[:training_end_period])
    optimized = stat.calc_port_return(dates_list=pd.to_datetime(df_returns_matrix.loc[testing_start_period:].index), initial_ticker_weights=sol, tr_matrix=df_returns_matrix)

    # daily rebalance
    optimized_rebal = pd.DataFrame()
    dt_list = pd.to_datetime(df_returns_matrix.loc[testing_start_period:].index)
    for idx, _d in enumerate(dt_list):
        if _d == max(dt_list):
            break
        _sub_port = bench[bench["start_date"]==_d]
        _daily_bench_wt = dict(zip(_sub_port["ticker"], _sub_port["start_wt"]))

        # trains with the most recent dataset
        if _d == min(dt_list):
            _daily_opt_basket = opt.minimize_active_risk(benchmark_portfolio=_daily_bench_wt, cash_drag=_cash, tr_matrix=df_returns_matrix.loc[:training_end_period])
        else:
            _daily_opt_basket = opt.minimize_active_risk(benchmark_portfolio=_daily_bench_wt, cash_drag=_cash, tr_matrix=df_returns_matrix.loc[:dt_list[idx-1].strftime("%Y-%m-%d")])

        if optimized_rebal.empty:
            optimized_rebal = stat.calc_port_return(dates_list=[_d, dt_list[idx+1]], initial_ticker_weights=_daily_opt_basket, tr_matrix=df_returns_matrix)
        else:
            optimized_rebal = pd.concat([optimized_rebal, stat.calc_port_return(dates_list=[_d, dt_list[idx+1]], initial_ticker_weights=_daily_opt_basket, tr_matrix=df_returns_matrix)])

    # sum optimized portfolio return
    optimized["weighted_return"] = optimized["start_wt"]*optimized["period_return"]
    optimized_port_returns = optimized.groupby(by=["start_date", "end_date"], group_keys=True)[["weighted_return"]].apply(sum).reset_index()

    # sum optimized portfolio return
    optimized_rebal["weighted_return"] = optimized_rebal["start_wt"]*optimized_rebal["period_return"]
    optimized_rebal_port_returns = optimized_rebal.groupby(by=["start_date", "end_date"], group_keys=True)[["weighted_return"]].apply(sum).reset_index()

    # sum benchmark portfolio return
    bench["weighted_return"] = bench["start_wt"]*bench["period_return"]
    bench_port_returns = bench.groupby(by=["start_date", "end_date"], group_keys=True)[["weighted_return"]].apply(sum).reset_index()

    # sum default portfolio return
    default["weighted_return"] = default["start_wt"]*default["period_return"]
    default_port_returns = default.groupby(by=["start_date", "end_date"], group_keys=True)[["weighted_return"]].apply(sum).reset_index()

    # Consolidate and summarize the different portfolios
    comparison = bench_port_returns[["start_date", "end_date"]]
    comparison["bench"] = comparison["start_date"].map(dict(zip(bench_port_returns["start_date"], bench_port_returns["weighted_return"])))
    comparison["bench_cumprod"] = (1+comparison["bench"]).cumprod()-1
    comparison["optimized"] = comparison["start_date"].map(dict(zip(optimized_port_returns["start_date"], optimized_port_returns["weighted_return"])))
    comparison["optimized_cumprod"] = (1 + comparison["optimized"]).cumprod() - 1
    comparison["optimized_rebal"] = comparison["start_date"].map(dict(zip(optimized_rebal_port_returns["start_date"], optimized_rebal_port_returns["weighted_return"])))
    comparison["optimized_rebal_cumprod"] = (1 + comparison["optimized_rebal"]).cumprod() - 1
    comparison["default"] = comparison["start_date"].map(dict(zip(default_port_returns["start_date"], default_port_returns["weighted_return"])))
    comparison["default_cumprod"] = (1 + comparison["default"]).cumprod() - 1

    # Analysis Statistics
    print(f"Bench - Optimized Daily Std Dev: {1e4*(comparison['bench']-comparison['optimized']).std()}bps")
    print(f"Bench - Optimized Rebal Daily Std Dev: {1e4 * (comparison['bench'] - comparison['optimized_rebal']).std()}bps")
    print(f"Bench - Default Daily Std Dev: {1e4*(comparison['bench'] - comparison['default']).std()}bps")


    # Graph Results
    import matplotlib.pyplot as plt
    plt.figure(figsize=(10, 6))

    plt.plot(pd.to_datetime(comparison["start_date"]), comparison["bench_cumprod"], label="bench")
    plt.plot(pd.to_datetime(comparison["start_date"]), comparison["optimized_cumprod"], label="optimized")
    plt.plot(pd.to_datetime(comparison["start_date"]), comparison["optimized_rebal_cumprod"], label="optimized")
    plt.plot(pd.to_datetime(comparison["start_date"]), comparison["default_cumprod"], label="default")

    plt.title('Portfolio Returns Optimization Vs. Default')
    plt.xlabel('Date')
    plt.ylabel('Return')
    plt.legend(loc='upper left')

    plt.show()



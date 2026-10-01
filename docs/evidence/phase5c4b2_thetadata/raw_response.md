Hi Manuel,

Thanks for the detailed list. I kept your IDs and grouped the ones that share the same answer. Everything below is based on the current v3 documentation and the response schemas, linked where relevant.

PIT-01, PIT-02, PIT-03, PIT-04 (trades, quotes, OI, index)

Historical responses come from a single stored copy of each trading day, as received from the feed. We don't keep or expose prior versions, revision timestamps or an as-of-download parameter on any history endpoint. Cancels and corrections that OPRA disseminates are not applied back onto the original record. They arrive as records of their own, with their own timestamp and condition code, and the original trade stays in the raw trade endpoint. So for exchange-originated corrections the tape is causal by construction. The classification of the stored copy itself is your call, based on the fact that no versions are exposed.

PIT-05, PIT-06, GRK-02, GRK-05 (Greeks and IV)

Greeks and IV are not stored outputs. They are calculated when you make the request, from the stored option NBBO and the underlying price at the matching timestamp. That's why the rate, dividend and version parameters can change the result. A value downloaded today reflects today's methodology. When the methodology changed (for example the under-7-DTE time-to-expiration change), the legacy behavior stayed available through a parameter (version=1). Prior outputs are not kept separately, but every input is exposed, so you can rebuild them locally.

[https://docs.thetadata.us/Articles/Data-And-Requests/Option-Greeks.html](https://docs.thetadata.us/Articles/Data-And-Requests/Option-Greeks.html)

TIM-01, TRD-01, QTE-01, IDX-01 (clocks)

The timestamp on option trades, option quotes, OI and index prices is the exchange timestamp carried on the feed message. It has millisecond precision and is expressed in US Eastern time (America/New_York, so it follows DST), in the format YYYY-MM-DDTHH\:mm\:ss.SSS. trade_quote returns both trade_timestamp and quote_timestamp. The Greeks endpoints return the option timestamp plus underlying_timestamp. No endpoint exposes a receipt, processing or client dissemination time.

TIM-02

We don't publish a guaranteed maximum delay between the event timestamp and client availability. The documented figure is that we receive the OPRA feed in real time with latencies averaging under 3ms. That's an average, not a bound.

[https://docs.thetadata.us/Articles/Data-And-Requests/The-SIPs.html](https://docs.thetadata.us/Articles/Data-And-Requests/The-SIPs.html)

OI-01, OI-02

open_interest is the value from OPRA's daily open interest message for that contract. It represents the open interest at the end of the previous trading day. A row stamped on trading date D (normally around 06:30 ET) carries the close of the prior trading day, so a Monday morning row reflects Friday's close.

OI-03, OI-08

There is no separate availability or revision timestamp. Each row carries the timestamp of the OPRA message itself (for example 2024-11-04T06:30:04), at the same precision and timezone described above. That gives you a per-contract, per-day timestamp rather than only the 06:30 convention.

OI-04

We don't publish a written guarantee or SLA that session-D OI is available to all clients before 09:30 ET.

OI-05, OI-06, OI-07

OPRA may send no message for a contract with no open interest. In that case there is simply no row, because we never fill in zeros, so a 0 in the response is a 0 that OPRA reported. If OPRA sends more than one OI message for a contract on a day, each one is returned as its own row with its own timestamp. Earlier rows are not overwritten. There is no flag marking a message as a correction.

OI-09

To get what was known at time T, take the latest row with timestamp <= T for that contract and date. Using the example from the endpoint page: AAPL 2024-11-08 220 C on 2024-11-04 has one row at 06:30:04 with 2732, so the as-of value at 09:30, 10:00 and 11:00 is 2732.

[https://docs.thetadata.us/operations/option_history_open_interest.html](https://docs.thetadata.us/operations/option_history_open_interest.html)

TRD-02, TRD-04

sequence is the exchange sequence from the feed. It is a signed 32-bit value that wraps around, so it is not unique across contracts, exchanges or days, and it is not a global identity. We don't publish a deduplication key or a total ordering contract beyond timestamp plus sequence, and several records can share the same millisecond.

[https://docs.thetadata.us/Articles/Data-And-Requests/Making-Requests.html#trade-sequences](https://docs.thetadata.us/Articles/Data-And-Requests/Making-Requests.html#trade-sequences)

TRD-03

Late reports, cancels and corrections are identified by the trade condition code: 2 OUT_OF_SEQ and the other codes in the Late Report column, 40 to 44 for the cancel variants, 61 ADMIN, and 117 CORRECTED_CS_LAST. There is no field that links a cancel to the record it cancels.

[https://docs.thetadata.us/Articles/Errors-Exchanges-Conditions/Trade-Conditions.html](https://docs.thetadata.us/Articles/Errors-Exchanges-Conditions/Trade-Conditions.html)

[https://docs.thetadata.us/Articles/Data-And-Requests/OHLC-EOD.html](https://docs.thetadata.us/Articles/Data-And-Requests/OHLC-EOD.html)

TRD-05, QTE-05

A historical download returns the stored tape for the day. It is not a recording of what a specific client session received, and since no availability clock is exposed, "received by T" can only be approximated from the event timestamp plus your own latency assumption.

QTE-02, QTE-03, QTE-04

Option quote rows are the OPRA NBBO. Each row is one update carrying both sides, with bid/ask price, size in contracts, exchange and condition. Quote records have no sequence field. Apart from the equities case on the Data Issues page, we don't document any quote filtering, and option NBBO quotes are returned as OPRA sent them, including zero bids or asks premarket.

[https://docs.thetadata.us/operations/option_history_quote.html](https://docs.thetadata.us/operations/option_history_quote.html)

[https://docs.thetadata.us/Articles/Data-And-Requests/Data-Issues.html](https://docs.thetadata.us/Articles/Data-And-Requests/Data-Issues.html)

IDX-02, IDX-03, IDX-04

SPX comes from the Cboe Global Indices Feed at the resolution it is reported, which is about one print per second. No new tick is recorded when the value doesn't change, and there are no gap or coverage flags. The PIT-04 note above applies here too. Index and OPRA are separate feeds with their own exchange timestamps and no shared sequence, so they need to be aligned by timestamp. The Greeks endpoints do exactly that and return underlying_timestamp so you can check the pairing.

[https://docs.thetadata.us/operations/index_history_price.html](https://docs.thetadata.us/operations/index_history_price.html)

GRK-01

Implied volatility and first order Greeks are Standard and up. First order does not include gamma. Gamma and the rest of the second order Greeks are Pro, as are third order Greeks and the per-trade Greeks. Greeks EOD (one record per contract per day, gamma included) is available on Standard. Historical Greeks on index options start 2017-01-01.

GRK-03, GRK-04

The model is European Black-Scholes. Dividends are zero unless you pass annual_dividend. Time to expiration uses calendar days over 365, and under 7 DTE it is measured from the quote timestamp. IV is solved from the option mid. For SPX options the underlying is the index price at the matching timestamp. The default rate is SOFR. For historical dates it uses the SOFR value of that date, which the NY Fed publishes the next business day at around 8am ET, so for strict causality pass your own rate with rate_value. Each row exposes the option timestamp, bid, ask, underlying_price and underlying_timestamp. A model version identifier and a compute time are not exposed. The SOFR series itself is available at [https://docs.thetadata.us/operations/interest_rate_history_eod.html](https://docs.thetadata.us/operations/interest_rate_history_eod.html)

SYM-01, SYM-02, SYM-03

SPX and SPXW are separate roots, exactly as OPRA reports them, and a contract is identified by symbol, expiration, strike and right. SPXPM stopped being used on 2018-12-21. Before 2022-05-16, SPXW only had Monday, Wednesday and Friday expirations. SPX is AM-settled, so it has no data on its expiration date. Contract metadata is not versioned, and there are no listing or delisting timestamps. For a historical 0DTE universe, option/list/contracts/trade or /quote with date=D returns every contract traded or quoted on D, and you can filter SPXW where expiration equals D.

[https://docs.thetadata.us/Articles/Data-And-Requests/Symbology.html](https://docs.thetadata.us/Articles/Data-And-Requests/Symbology.html)

[https://docs.thetadata.us/operations/option_list_contracts.html](https://docs.thetadata.us/operations/option_list_contracts.html)

ENT-01, ENT-02

Options: Value gives 1-minute history from 2020-01-01 with quote, OHLC, OI and EOD. Standard gives tick level from 2016-01-01 and adds trades, trade_quote, IV and first order Greeks. Pro gives tick level from 2012-06-01 plus second and third order and the trade Greeks. SPX index history is a separate Indices subscription: Value is 1-minute from 2023-01-01 with a 15-minute delay, Standard is venue resolution from 2022-01-01, and Pro is venue resolution from 2017-01-01.

[https://docs.thetadata.us/Articles/Getting-Started/Subscriptions.html](https://docs.thetadata.us/Articles/Getting-Started/Subscriptions.html)

Regards,

Eduardo

Eduardo • 28 min

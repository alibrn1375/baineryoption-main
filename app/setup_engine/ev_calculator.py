"""Binary Options Expected Value (EV) calculator."""

from app.models.binary_decision import EVResult, ExpectancyStatus


class EVCalculator:
    """Calculates mathematical Expected Value (EV) for fixed-payout binary contracts."""

    @staticmethod
    def calculate_ev(
        win_probability: float,
        conservative_probability: float,
        payout_rate: float,
        risk_per_unit: float = 1.0
    ) -> EVResult:
        """Formula:
        
        EV = (P_win * payout) - ((1 - P_win) * risk)
        Break-even Probability = risk / (risk + payout) = 1 / (1 + payout)
        """
        if payout_rate <= 0.0 or conservative_probability <= 0.0:
            return EVResult(
                probability=win_probability,
                conservative_probability=conservative_probability,
                payout=payout_rate,
                expected_value=-1.0,
                break_even_probability=1.0,
                status=ExpectancyStatus.INSUFFICIENT_DATA
            )

        break_even_p = risk_per_unit / (risk_per_unit + payout_rate)

        # Expected value calculated on conservative Wilson-penalized probability
        loss_p = 1.0 - conservative_probability
        ev = (conservative_probability * payout_rate) - (loss_p * risk_per_unit)

        if ev > 0.0 and conservative_probability > break_even_p:
            status = ExpectancyStatus.POSITIVE_EXPECTANCY
        else:
            status = ExpectancyStatus.NEGATIVE_EXPECTANCY

        return EVResult(
            probability=round(win_probability, 4),
            conservative_probability=round(conservative_probability, 4),
            payout=round(payout_rate, 4),
            expected_value=round(ev, 4),
            break_even_probability=round(break_even_p, 4),
            status=status
        )

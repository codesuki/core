# take action on the result of a model.
# either BUY or SELL.


class ModelActionTaker:
    def __init__(self, order_management_system):
        self.oms = order_management_system

    def take_trading_action(self, model_output):
        # DUMB
        if model_output['buy_confidence'] + model_output['sell_confidence'] != 1:
            raise Exception('buy_confidence and sell_confidence do not add to 1.')
        if model_output['buy_confidence'] > 0.9:
            self.oms.send_buy_order(amount=0.01)
        elif model_output['sell_confidence'] > 0.9:
            self.oms.send_sell_order(amount=0.01)
        else:
            pass

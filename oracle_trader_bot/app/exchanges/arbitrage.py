# app/exchanges/arbitrage.py
import asyncio
import logging
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from .manager import ExchangeManager
from .base import OrderSide, OrderType


logger = logging.getLogger(__name__)


@dataclass
class ArbitrageOpportunity:
    """Represents an arbitrage opportunity."""
    symbol: str
    buy_exchange: str
    sell_exchange: str
    buy_price: float
    sell_price: float
    profit_percentage: float
    max_amount: float
    timestamp: int


class ArbitrageService:
    """
    Service for detecting and executing arbitrage opportunities.
    
    Features:
    - Real-time opportunity detection
    - Risk management
    - Automatic execution
    - Performance tracking
    """
    
    def __init__(self, exchange_manager: ExchangeManager):
        self.exchange_manager = exchange_manager
        self.min_profit_percentage = 0.5  # Minimum 0.5% profit
        self.max_position_size = 1000  # Max USD per arbitrage
        self.is_running = False
        self.opportunities_found = 0
        self.trades_executed = 0
        self.total_profit = 0.0
        
    async def scan_opportunities(self, symbols: List[str]) -> List[ArbitrageOpportunity]:
        """
        Scan for arbitrage opportunities across multiple symbols.
        
        Args:
            symbols: List of trading pairs to scan
            
        Returns:
            List of arbitrage opportunities
        """
        opportunities = []
        
        for symbol in symbols:
            try:
                exchange_opportunities = await self.exchange_manager.find_arbitrage_opportunities(
                    symbol, self.min_profit_percentage
                )
                
                for opp in exchange_opportunities:
                    # Calculate maximum safe amount based on orderbook depth
                    max_amount = await self._calculate_max_amount(opp)
                    
                    if max_amount > 0:
                        arbitrage_opp = ArbitrageOpportunity(
                            symbol=opp['symbol'],
                            buy_exchange=opp['buy_exchange'],
                            sell_exchange=opp['sell_exchange'],
                            buy_price=opp['buy_price'],
                            sell_price=opp['sell_price'],
                            profit_percentage=opp['profit_percentage'],
                            max_amount=max_amount,
                            timestamp=opp['timestamp']
                        )
                        opportunities.append(arbitrage_opp)
                        
            except Exception as e:
                logger.error(f"Error scanning {symbol}: {str(e)}")
                continue
        
        # Sort by profit percentage
        opportunities.sort(key=lambda x: x.profit_percentage, reverse=True)
        self.opportunities_found += len(opportunities)
        
        return opportunities
    
    async def execute_arbitrage(self, opportunity: ArbitrageOpportunity, amount_usd: float) -> Dict[str, Any]:
        """
        Execute an arbitrage opportunity.
        
        Args:
            opportunity: The arbitrage opportunity to execute
            amount_usd: USD amount to trade
            
        Returns:
            Execution result with profit/loss information
        """
        if amount_usd > opportunity.max_amount:
            amount_usd = opportunity.max_amount
        
        if amount_usd > self.max_position_size:
            amount_usd = self.max_position_size
        
        # Calculate amount in base currency
        amount_base = amount_usd / opportunity.buy_price
        
        try:
            # Execute buy and sell orders simultaneously
            buy_task = self._place_buy_order(opportunity, amount_base)
            sell_task = self._place_sell_order(opportunity, amount_base)
            
            buy_result, sell_result = await asyncio.gather(buy_task, sell_task)
            
            # Calculate actual profit
            buy_cost = buy_result.get('amount', 0) * buy_result.get('price', opportunity.buy_price)
            sell_revenue = sell_result.get('amount', 0) * sell_result.get('price', opportunity.sell_price)
            profit = sell_revenue - buy_cost
            
            self.trades_executed += 1
            self.total_profit += profit
            
            result = {
                "success": True,
                "opportunity": opportunity,
                "buy_order": buy_result,
                "sell_order": sell_result,
                "profit_usd": profit,
                "profit_percentage": (profit / buy_cost) * 100 if buy_cost > 0 else 0,
                "execution_time": buy_result.get('timestamp', 0)
            }
            
            logger.info(f"Arbitrage executed: {profit:.2f} USD profit on {opportunity.symbol}")
            return result
            
        except Exception as e:
            logger.error(f"Failed to execute arbitrage: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "opportunity": opportunity
            }
    
    async def _place_buy_order(self, opportunity: ArbitrageOpportunity, amount: float) -> Dict[str, Any]:
        """Place buy order on the cheaper exchange."""
        order_data = {
            "symbol": opportunity.symbol,
            "side": OrderSide.BUY,
            "type": OrderType.MARKET,
            "amount": amount
        }
        
        return await self.exchange_manager.place_order(order_data, opportunity.buy_exchange)
    
    async def _place_sell_order(self, opportunity: ArbitrageOpportunity, amount: float) -> Dict[str, Any]:
        """Place sell order on the more expensive exchange."""
        order_data = {
            "symbol": opportunity.symbol,
            "side": OrderSide.SELL,
            "type": OrderType.MARKET,
            "amount": amount
        }
        
        return await self.exchange_manager.place_order(order_data, opportunity.sell_exchange)
    
    async def _calculate_max_amount(self, opportunity: Dict[str, Any]) -> float:
        """
        Calculate maximum safe amount for arbitrage based on orderbook depth.
        
        Args:
            opportunity: Arbitrage opportunity data
            
        Returns:
            Maximum USD amount that can be safely traded
        """
        try:
            # Get orderbooks from both exchanges
            buy_exchange = opportunity['buy_exchange']
            sell_exchange = opportunity['sell_exchange']
            symbol = opportunity['symbol']
            
            buy_orderbook = await self.exchange_manager.exchanges[buy_exchange].get_orderbook(symbol, 10)
            sell_orderbook = await self.exchange_manager.exchanges[sell_exchange].get_orderbook(symbol, 10)
            
            # Calculate depth on buy side (asks)
            buy_depth = 0
            for price, amount in buy_orderbook['asks'][:5]:  # Top 5 levels
                buy_depth += price * amount
            
            # Calculate depth on sell side (bids)
            sell_depth = 0
            for price, amount in sell_orderbook['bids'][:5]:  # Top 5 levels
                sell_depth += price * amount
            
            # Use 10% of the minimum depth to avoid slippage
            max_amount = min(buy_depth, sell_depth) * 0.1
            
            return min(max_amount, self.max_position_size)
            
        except Exception as e:
            logger.warning(f"Failed to calculate max amount: {str(e)}")
            # Default to small amount if calculation fails
            return 100.0
    
    async def start_monitoring(self, symbols: List[str], scan_interval: float = 5.0):
        """
        Start continuous monitoring for arbitrage opportunities.
        
        Args:
            symbols: List of symbols to monitor
            scan_interval: Seconds between scans
        """
        self.is_running = True
        logger.info(f"Starting arbitrage monitoring for {len(symbols)} symbols")
        
        while self.is_running:
            try:
                opportunities = await self.scan_opportunities(symbols)
                
                if opportunities:
                    logger.info(f"Found {len(opportunities)} arbitrage opportunities")
                    
                    # Execute the best opportunity if profitable enough
                    best_opportunity = opportunities[0]
                    if best_opportunity.profit_percentage >= self.min_profit_percentage:
                        await self.execute_arbitrage(best_opportunity, 100.0)  # Trade $100
                
                await asyncio.sleep(scan_interval)
                
            except Exception as e:
                logger.error(f"Error in arbitrage monitoring: {str(e)}")
                await asyncio.sleep(scan_interval)
    
    def stop_monitoring(self):
        """Stop arbitrage monitoring."""
        self.is_running = False
        logger.info("Stopped arbitrage monitoring")
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get arbitrage performance statistics."""
        return {
            "opportunities_found": self.opportunities_found,
            "trades_executed": self.trades_executed,
            "total_profit_usd": self.total_profit,
            "average_profit_per_trade": self.total_profit / max(self.trades_executed, 1),
            "success_rate": (self.trades_executed / max(self.opportunities_found, 1)) * 100,
            "is_running": self.is_running
        }
    
    def update_settings(self, min_profit_percentage: Optional[float] = None, 
                       max_position_size: Optional[float] = None):
        """Update arbitrage settings."""
        if min_profit_percentage is not None:
            self.min_profit_percentage = min_profit_percentage
            logger.info(f"Updated min profit percentage to {min_profit_percentage}%")
        
        if max_position_size is not None:
            self.max_position_size = max_position_size
            logger.info(f"Updated max position size to ${max_position_size}")


# Singleton instance
arbitrage_service: Optional[ArbitrageService] = None


def get_arbitrage_service(exchange_manager: ExchangeManager) -> ArbitrageService:
    """Get or create arbitrage service instance."""
    global arbitrage_service
    if arbitrage_service is None:
        arbitrage_service = ArbitrageService(exchange_manager)
    return arbitrage_service
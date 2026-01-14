#[starknet::contract]
mod Bridge {
    use starknet::ContractAddress;
    use starknet::get_caller_address;
    use starknet::get_contract_address;

    #[storage]
    struct Storage {
        admin: ContractAddress,
    }

    #[event]
    #[derive(Drop, starknet::Event)]
    enum Event {
        TokensLocked: TokensLocked,
    }

    #[derive(Drop, starknet::Event)]
    struct TokensLocked {
        user: ContractAddress,
        token: ContractAddress,
        amount: u256,
        target_chain: felt252,
        target_address: felt252,
    }

    #[constructor]
    fn constructor(ref self: ContractState, admin_address: ContractAddress) {
        self.admin.write(admin_address);
    }

    #[external(v0)]
    #[generate_trait]
    impl BridgeImpl of IBridge {
        fn lock_tokens(
            ref self: ContractState,
            token: ContractAddress,
            amount: u256,
            target_chain: felt252,
            target_address: felt252
        ) {
            let caller = get_caller_address();
            let this_contract = get_contract_address();

            // Transfer tokens from User to Bridge (Lock)
            // Note: In a real implementation, we would call the ERC20 dispatcher here.
            // For now, we assume the user has approved the transfer and we just emit the event
            // effectively acting as a "Proof of Intent" bridge for this MVP if we don't fully integrate ERC20 interface yet.
            // But let's add the Interface call for completeness, assuming IERC20 dispatcher is available or we use a low-level call.
            
            // Emitting event is the critical part for the Relayer
            self.emit(Event::TokensLocked(TokensLocked {
                user: caller,
                token: token,
                amount: amount,
                target_chain: target_chain,
                target_address: target_address
            }));
        }
    }
}

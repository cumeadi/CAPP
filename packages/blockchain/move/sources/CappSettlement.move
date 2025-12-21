module capp::settlement {
    use std::signer;
    use std::string::String;
    use aptos_framework::coin;
    use aptos_framework::aptos_coin::AptosCoin;
    use aptos_std::table::{Self, Table};
    use aptos_framework::account;

    /// Error codes
    const E_NOT_ADMIN: u64 = 1;
    const E_PAYMENT_NOT_FOUND: u64 = 2;
    const E_SETTLEMENT_EXISTS: u64 = 3;

    /// Main storage for active settlements
    struct SettlementStore has key {
        // Maps payment_id -> Escrowed Coins
        payments: Table<String, coin::Coin<AptosCoin>>,
        // Maps payment_id -> Sender address (for refunds)
        senders: Table<String, address>,
        admin: address
    }

    /// Initialize the module (called once by deployer)
    public entry fun init_module(admin: &signer) {
        move_to(admin, SettlementStore {
            payments: table::new(),
            senders: table::new(),
            admin: signer::address_of(admin)
        });
    }

    /// Create a new settlement (Escrow funds)
    public entry fun initialize_settlement(
        sender: &signer,
        payment_id: String,
        amount: u64
    ) acquires SettlementStore {
        let store = borrow_global_mut<SettlementStore>(@capp);
        
        // Ensure payment ID doesn't exist
        assert!(!table::contains(&store.payments, payment_id), E_SETTLEMENT_EXISTS);

        // Withdraw funds from sender
        let funds = coin::withdraw<AptosCoin>(sender, amount);

        // Store funds and sender info
        table::add(&mut store.payments, payment_id, funds);
        table::add(&mut store.senders, payment_id, signer::address_of(sender));
    }

    /// Release funds to recipient (Called by Admin/AI Agent)
    public entry fun release_funds(
        admin: &signer,
        payment_id: String,
        recipient: address
    ) acquires SettlementStore {
        let store = borrow_global_mut<SettlementStore>(@capp);
        
        // Verify Admin
        assert!(signer::address_of(admin) == store.admin, E_NOT_ADMIN);
        
        // Verify payment exists
        assert!(table::contains(&store.payments, payment_id), E_PAYMENT_NOT_FOUND);

        // Extract funds
        let funds = table::remove(&mut store.payments, payment_id);
        let _sender = table::remove(&mut store.senders, payment_id); // Cleanup sender mapping

        // Deposit to recipient
        coin::deposit(recipient, funds);
    }

    /// Refund funds back to sender (Called by Admin/AI Agent if compliance fails)
    public entry fun refund_sender(
        admin: &signer,
        payment_id: String
    ) acquires SettlementStore {
        let store = borrow_global_mut<SettlementStore>(@capp);
        
        // Verify Admin
        assert!(signer::address_of(admin) == store.admin, E_NOT_ADMIN);
        
        // Verify payment exists
        assert!(table::contains(&store.payments, payment_id), E_PAYMENT_NOT_FOUND);

        // Extract funds
        let funds = table::remove(&mut store.payments, payment_id);
        let sender = table::remove(&mut store.senders, payment_id);

        // Return to sender
        coin::deposit(sender, funds);
    }
}

#include "world_interface.hpp"
namespace test_world
{
    using namespace sg;

    class GenBase
    {
      protected:
        GenBase( const PInstance & _p ) : p(_p) {}
        PInstance p;
      public:
        const PInstance & _gp() const { return p; }  
    };


    
    class Position : public GenBase
    {
      public:
        enum { ID = 1 };
      
        Position( const PInstance & _p ) : GenBase(_p) {}

        double latitude() const { return p->getDouble( AttributeID(0,0) ); }
        void latitude( double v ) { p->setDouble( AttributeID(0,0), v ); }


        double longitude() const { return p->getDouble( AttributeID(0,1) ); }
        void longitude( double v ) { p->setDouble( AttributeID(0,1), v ); }


        double altitude() const { return p->getDouble( AttributeID(0,2) ); }
        void altitude( double v ) { p->setDouble( AttributeID(0,2), v ); }
    };



    
    class Orientation : public GenBase
    {
      public:
        enum { ID = 2 };
      
        Orientation( const PInstance & _p ) : GenBase(_p) {}

        float roll() const { return p->getFloat( AttributeID(0,0) ); }
        void roll( float v ) { p->setFloat( AttributeID(0,0), v ); }


        float pitch() const { return p->getFloat( AttributeID(0,1) ); }
        void pitch( float v ) { p->setFloat( AttributeID(0,1), v ); }


        float yaw() const { return p->getFloat( AttributeID(0,2) ); }
        void yaw( float v ) { p->setFloat( AttributeID(0,2), v ); }
    };



    
    class Location : public GenBase
    {
      public:
        enum { ID = 3 };
      
        Location( const PInstance & _p ) : GenBase(_p) {}

        Position pos() const { return Position(p->getInstance( AttributeID(0,0) )); }


        Orientation ori() const { return Orientation(p->getInstance( AttributeID(0,1) )); }
    };



    
    class PhysicalEntity : public GenBase
    {
      public:
        enum { ID = 4 };
      
        PhysicalEntity( const PInstance & _p ) : GenBase(_p) {}

        Location loc() const { return Location(p->getInstance( AttributeID(0,0) )); }
    };


    class PhysicalEntityObject
    {
       PObject o;
       friend class sg::WorldInterface;     
       PhysicalEntityObject( PObject _o ) : o(_o) {}
       
     public:
       enum { ID = 4 };

       PhysicalEntityObject( const PhysicalEntityObject & x ) : o(x.o) {}
       
       const UUID *  getUUID() const { return o->getUUID(); }
       PhysicalEntity getInstance() { return PhysicalEntity( o->getInstance() ); }
       const PhysicalEntity getInstance() const { return PhysicalEntity( o->getInstance() ); }
    };



    
    class Vehicle : public PhysicalEntity
    {
      public:
        enum { ID = 5 };
      
        Vehicle( const PInstance & _p ) : PhysicalEntity(_p) {}

        uint32_t max_fuel() const { return p->getUInt32( AttributeID(1,0) ); }
        void max_fuel( uint32_t v ) { p->setUInt32( AttributeID(1,0), v ); }


        bool empty() const { return p->getBoolean( AttributeID(1,1) ); }
        void empty( bool v ) { p->setBoolean( AttributeID(1,1), v ); }


        uint32_t current_fuel() const { return p->getUInt32( AttributeID(1,2) ); }
        void current_fuel( uint32_t v ) { p->setUInt32( AttributeID(1,2), v ); }


        bool is_moving() const { return p->getBoolean( AttributeID(1,3) ); }
        void is_moving( bool v ) { p->setBoolean( AttributeID(1,3), v ); }
    };


    class VehicleObject
    {
       PObject o;
       friend class sg::WorldInterface;     
       VehicleObject( PObject _o ) : o(_o) {}
       
     public:
       enum { ID = 5 };

       VehicleObject( const VehicleObject & x ) : o(x.o) {}
       
       const UUID *  getUUID() const { return o->getUUID(); }
       Vehicle getInstance() { return Vehicle( o->getInstance() ); }
       const Vehicle getInstance() const { return Vehicle( o->getInstance() ); }
    };



    
    class Aircraft : public Vehicle
    {
      public:
        enum { ID = 6 };
      
        Aircraft( const PInstance & _p ) : Vehicle(_p) {}

        bool gear_down() const { return p->getBoolean( AttributeID(2,0) ); }
        void gear_down( bool v ) { p->setBoolean( AttributeID(2,0), v ); }


        const ByteString * callsign() const { return p->getByteString( AttributeID(2,1) ); }
        void callsign( const ByteString * v ) { p->setByteString( AttributeID(2,1), v ); }
        void callsign( const char * v ) { p->setByteString( AttributeID(2,1), v ); }
        void callsign( const std::string & v ) { p->setByteString( AttributeID(2,1), v ); }
        void callsign( const uint8_t * v, std::size_t nbytes ) { p->setByteString( AttributeID(2,1), v, nbytes ); }
    };


    class AircraftObject
    {
       PObject o;
       friend class sg::WorldInterface;     
       AircraftObject( PObject _o ) : o(_o) {}
       
     public:
       enum { ID = 6 };

       AircraftObject( const AircraftObject & x ) : o(x.o) {}
       
       const UUID *  getUUID() const { return o->getUUID(); }
       Aircraft getInstance() { return Aircraft( o->getInstance() ); }
       const Aircraft getInstance() const { return Aircraft( o->getInstance() ); }
    };



    
    class Automobile : public Vehicle
    {
      public:
        enum { ID = 7 };
      
        Automobile( const PInstance & _p ) : Vehicle(_p) {}

        ArrayWrapper<float> tire_pressure() const { return ArrayWrapper<float>(p->getInstance(AttributeID(2,0)),4); }
    };


    class AutomobileObject
    {
       PObject o;
       friend class sg::WorldInterface;     
       AutomobileObject( PObject _o ) : o(_o) {}
       
     public:
       enum { ID = 7 };

       AutomobileObject( const AutomobileObject & x ) : o(x.o) {}
       
       const UUID *  getUUID() const { return o->getUUID(); }
       Automobile getInstance() { return Automobile( o->getInstance() ); }
       const Automobile getInstance() const { return Automobile( o->getInstance() ); }
    };



    
    class VehicleOrder : public GenBase
    {
      public:
        enum { ID = 8 };
      
        VehicleOrder( const PInstance & _p ) : GenBase(_p) {}

        const UUID * vehicle_id() const { return p->getUUID( AttributeID(0,0) ); }
        void vehicle_id( const UUID * v ) { p->setUUID( AttributeID(0,0), v ); }
    };


    class VehicleOrderMessage
    {
       PObject o;
       friend class sg::World;     
       VehicleOrderMessage( PObject _o ) : o(_o) {}
       
     public:
       enum { ID = 8 };
       
       const UUID * getUUID() const { return o->getUUID(); }
       VehicleOrder getInstance() { return VehicleOrder( o->getInstance() ); }
       const VehicleOrder getInstance() const { return VehicleOrder( o->getInstance() ); }
    };



    
    class MoveTo : public VehicleOrder
    {
      public:
        enum { ID = 9 };
      
        MoveTo( const PInstance & _p ) : VehicleOrder(_p) {}

        Position destination() const { return Position(p->getInstance( AttributeID(1,0) )); }
    };


    class MoveToMessage
    {
       PObject o;
       friend class sg::World;     
       MoveToMessage( PObject _o ) : o(_o) {}
       
     public:
       enum { ID = 9 };
       
       const UUID * getUUID() const { return o->getUUID(); }
       MoveTo getInstance() { return MoveTo( o->getInstance() ); }
       const MoveTo getInstance() const { return MoveTo( o->getInstance() ); }
    };



} // end namespace test_world



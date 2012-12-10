
#include <iostream>

#include "t.hpp"

#include "abidos.hpp"

using namespace std;
using namespace test_world;

class TestModel : public abidos::AbidosModel
{
   sg::PWorldInterface wi;
   int ncall;
   AircraftObject *po;
   
  public:

   TestModel( abidos::World * world );

   void tick();

   void first_tick();
   void second_tick();
   void default_tick();
};


TestModel::TestModel( abidos::World * world ) :
      wi(0),
      ncall(0),
      po(0)
{
   wi = abidos::createWorldInterface( "model_iface", world );
}


void TestModel::tick()
{
   switch( ncall )
   {
    case 0:
       first_tick();
       break;
    case 1:
       second_tick();
       break;
    default:
       default_tick();
   }

   ++ncall;
}


//--------------------------------------------------------------------

void test_cb( sg::PObject obj )
{
   cerr << "C++ %%% CALLBACK FUNCTION!! %%%" << endl;
}

void test2_cb( const VehicleObject & v )
{
   cerr << "C++ %%%%% EXACT CALLBACK %%%%" << endl;
   cerr << "   FQ Latitude: " << v.getInstance().loc().pos().longitude() << endl;
}


void TestModel::first_tick()
{
   cerr << "C++ First tick" << endl;

   wi->setNewObjectHandler( PhysicalEntity::ID, test_cb );
   
   wi->setNewObjectHandler< VehicleObject >( test2_cb );
   
   cerr << "   %% Running Callbacks (should be empty) %% " << endl;
   
   wi->runCallbacks();
   
   po = new AircraftObject( wi->createObject<AircraftObject>() );
    
   cerr << "   ******* object created ********" << endl;

   cerr << "   FQ Latitude: " << po->getInstance().loc().pos().longitude() << endl;
}

void TestModel::second_tick()
{
   cerr << "C++ Second tick" << endl;
   PhysicalEntity pe = po->getInstance();
        
   Location l = pe.loc();
    
   Position p = l.pos();
    
   cerr << "   Lat, lon, alt = " << p.latitude() << ", " << p.longitude() << ", " << p.altitude() << endl;
    
   p.latitude( 3.14159 );
        
   cerr << "   Lat, lon, alt = " << p.latitude() << ", " << p.longitude() << ", " << p.altitude() << endl;
}

void TestModel::default_tick()
{
   cerr << "C++ Default tick" << endl;
   cerr << "   FQ Latitude: " << po->getInstance().loc().pos().longitude() << endl;
}


extern "C"
{
   abidos::AbidosModel * new_test_model( abidos::World * world )
   {
      return new TestModel( world );
   }
}
